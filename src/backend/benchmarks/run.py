from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

from langchain_openai import ChatOpenAI

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from benchmarks.datasets import load_benchmark_questions
from config import benchmarks_enabled
from db import DATABASE_URL
from schemas import BenchmarkMode
from services.benchmark_runner import BenchmarkRunner, DEFAULT_DATASET_ROOT
from services.vector_store_service import get_vector_store
from utils.embeddings import get_embedding_model

logger = logging.getLogger(__name__)

DEFAULT_COLLECTION_NAME = os.getenv("VECTOR_COLLECTION_NAME", "agent_search_internal_data")
DEFAULT_MODEL_NAME = os.getenv("RUNTIME_AGENT_MODEL", "gpt-4.1-mini").strip() or "gpt-4.1-mini"
DEFAULT_MODEL_TEMPERATURE = float(os.getenv("DECOMPOSITION_ONLY_TEMPERATURE", "0"))


def _parse_metadata(values: list[str]) -> dict[str, Any]:
    metadata: dict[str, Any] = {}
    for raw_item in values:
        if "=" not in raw_item:
            raise ValueError(f"Invalid metadata item: {raw_item!r}. Expected key=value.")
        key, value = raw_item.split("=", 1)
        normalized_key = key.strip()
        if not normalized_key:
            raise ValueError(f"Invalid metadata key in: {raw_item!r}.")
        metadata[normalized_key] = value.strip()
    return metadata


def _dataset_path(dataset_root: Path, dataset_id: str) -> Path:
    return dataset_root / dataset_id / "questions.jsonl"


def _prepare_subset_dataset(
    *,
    source_dataset_id: str,
    source_dataset_root: Path,
    max_questions: int,
    target_root: Path,
) -> tuple[str, int]:
    source_path = _dataset_path(source_dataset_root, source_dataset_id)
    questions = load_benchmark_questions(source_path)
    subset_questions = questions[:max_questions]

    subset_dataset_id = f"{source_dataset_id}__subset_{max_questions}"
    target_dataset_path = _dataset_path(target_root, subset_dataset_id)
    target_dataset_path.parent.mkdir(parents=True, exist_ok=True)
    with target_dataset_path.open("w", encoding="utf-8") as handle:
        for question in subset_questions:
            handle.write(question.model_dump_json() + "\n")

    logger.info(
        "Prepared benchmark subset dataset source_dataset_id=%s subset_dataset_id=%s requested_max_questions=%s selected_questions=%s path=%s",
        source_dataset_id,
        subset_dataset_id,
        max_questions,
        len(subset_questions),
        target_dataset_path,
    )
    return subset_dataset_id, len(subset_questions)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run benchmark modes for a dataset and persist run results.")
    parser.add_argument("--dataset-id", required=True, help="Benchmark dataset id under benchmarks/datasets/<dataset-id>")
    parser.add_argument(
        "--mode",
        action="append",
        dest="modes",
        required=True,
        choices=[mode.value for mode in BenchmarkMode],
        help="Benchmark mode to execute. Repeat flag for multiple modes.",
    )
    parser.add_argument("--run-id", default=None, help="Optional explicit run id. Generated when omitted.")
    parser.add_argument(
        "--metadata",
        action="append",
        default=[],
        help="Attach run metadata key=value. Repeat flag for multiple metadata fields.",
    )
    parser.add_argument(
        "--max-questions",
        type=int,
        default=None,
        help="Optional question cap for operator smoke runs. Use 0 to validate setup without execution.",
    )
    parser.add_argument("--collection-name", default=DEFAULT_COLLECTION_NAME, help="PGVector collection name.")
    parser.add_argument("--model", default=DEFAULT_MODEL_NAME, help="Model name for benchmark execution.")
    parser.add_argument("--temperature", type=float, default=DEFAULT_MODEL_TEMPERATURE, help="Model temperature.")
    parser.add_argument("--dry-run", action="store_true", help="Validate inputs and print run plan without execution.")
    return parser


def _run_benchmark(
    *,
    dataset_root: Path,
    dataset_id: str,
    modes: list[BenchmarkMode],
    run_id: str | None,
    metadata: dict[str, Any],
    collection_name: str,
    model_name: str,
    temperature: float,
) -> dict[str, Any]:
    vector_store = get_vector_store(
        connection=DATABASE_URL,
        collection_name=collection_name,
        embeddings=get_embedding_model(),
    )
    model = ChatOpenAI(model=model_name, temperature=temperature)
    runner = BenchmarkRunner(dataset_root=dataset_root)

    logger.info(
        "Starting benchmark run cli dataset_id=%s mode_count=%s model=%s collection_name=%s run_id=%s",
        dataset_id,
        len(modes),
        model_name,
        collection_name,
        run_id,
    )
    summary = runner.run(
        dataset_id=dataset_id,
        modes=modes,
        vector_store=vector_store,
        model=model,
        run_id=run_id,
        metadata=metadata,
    )
    payload = {
        "run_id": summary.run_id,
        "dataset_id": summary.dataset_id,
        "mode_count": summary.mode_count,
        "question_count": summary.question_count,
        "completed_results": summary.completed_results,
    }
    logger.info(
        "Benchmark run cli completed run_id=%s dataset_id=%s completed_results=%s",
        summary.run_id,
        summary.dataset_id,
        summary.completed_results,
    )
    return payload


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO)
    args = _build_parser().parse_args(argv)
    if not benchmarks_enabled():
        raise SystemExit("Benchmarking is disabled. Set BENCHMARKS_ENABLED=true to run benchmark CLI commands.")

    try:
        metadata = _parse_metadata(args.metadata)
    except ValueError as exc:
        logger.error("Benchmark run cli invalid metadata error=%s", exc)
        raise SystemExit(str(exc)) from exc

    dataset_root = DEFAULT_DATASET_ROOT
    dataset_path = _dataset_path(dataset_root, args.dataset_id)
    if not dataset_path.exists():
        raise SystemExit(f"Benchmark dataset not found: {args.dataset_id}")

    all_questions = load_benchmark_questions(dataset_path)
    selected_modes = [BenchmarkMode(raw_mode) for raw_mode in args.modes]
    selected_question_count = len(all_questions)

    logger.info(
        "Benchmark run cli requested dataset_id=%s mode_count=%s run_id=%s max_questions=%s dry_run=%s",
        args.dataset_id,
        len(selected_modes),
        args.run_id,
        args.max_questions,
        args.dry_run,
    )

    if args.max_questions is not None:
        if args.max_questions < 0:
            raise SystemExit("--max-questions must be >= 0")
        selected_question_count = min(len(all_questions), args.max_questions)

    planned_payload = {
        "dataset_id": args.dataset_id,
        "modes": [mode.value for mode in selected_modes],
        "run_id": args.run_id,
        "question_count": len(all_questions),
        "selected_question_count": selected_question_count,
        "model": args.model,
        "temperature": args.temperature,
        "collection_name": args.collection_name,
        "metadata": metadata,
        "dry_run": args.dry_run,
    }
    if args.dry_run:
        logger.info("Benchmark run cli dry-run completed dataset_id=%s", args.dataset_id)
        print(json.dumps(planned_payload, sort_keys=True))
        return 0

    if args.max_questions is None:
        result_payload = _run_benchmark(
            dataset_root=dataset_root,
            dataset_id=args.dataset_id,
            modes=selected_modes,
            run_id=args.run_id,
            metadata=metadata,
            collection_name=args.collection_name,
            model_name=args.model,
            temperature=args.temperature,
        )
        print(json.dumps(result_payload, sort_keys=True))
        return 0

    with tempfile.TemporaryDirectory(prefix="benchmark_cli_dataset_") as tmp_dir:
        tmp_root = Path(tmp_dir)
        subset_dataset_id, subset_count = _prepare_subset_dataset(
            source_dataset_id=args.dataset_id,
            source_dataset_root=dataset_root,
            max_questions=args.max_questions,
            target_root=tmp_root,
        )
        logger.info(
            "Benchmark run cli executing subset dataset source_dataset_id=%s subset_dataset_id=%s subset_count=%s",
            args.dataset_id,
            subset_dataset_id,
            subset_count,
        )
        result_payload = _run_benchmark(
            dataset_root=tmp_root,
            dataset_id=subset_dataset_id,
            modes=selected_modes,
            run_id=args.run_id,
            metadata=metadata,
            collection_name=args.collection_name,
            model_name=args.model,
            temperature=args.temperature,
        )
        result_payload["source_dataset_id"] = args.dataset_id
        result_payload["selected_question_count"] = subset_count
        print(json.dumps(result_payload, sort_keys=True))
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
