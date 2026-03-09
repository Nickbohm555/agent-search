from __future__ import annotations

import argparse
import hashlib
import json
import logging
from pathlib import Path
from typing import Any, Callable

from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)


class PublicCorpusDocument(BaseModel):
    """One public corpus document used to generate benchmark question drafts."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    article: str = Field(min_length=1)
    url: str | None = None


class QuestionCandidateDraft(BaseModel):
    """Question draft shape requested from the generation model."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    question: str = Field(min_length=1)
    domain: str = Field(min_length=1)
    difficulty: str = Field(min_length=1)
    expected_answer_points: list[str] = Field(min_length=1)
    required_sources: list[str] = Field(min_length=1)
    disallowed_behaviors: list[str] = Field(min_length=1)


class GeneratedQuestionCandidate(QuestionCandidateDraft):
    """Candidate record that enters human review queue."""

    candidate_id: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    source_title: str = Field(min_length=1)
    source_url: str | None = None
    generator_model: str = Field(min_length=1)
    generation_prompt_version: str = Field(min_length=1)
    review_status: str = Field(default="pending_review", min_length=1)


def _default_model_invoker(model: str) -> Callable[[str], str]:
    from langchain_openai import ChatOpenAI

    llm = ChatOpenAI(model=model, temperature=0)

    def _invoke(prompt: str) -> str:
        response = llm.invoke(prompt)
        content = getattr(response, "content", response)
        if isinstance(content, list):
            return "".join(
                part.get("text", "") if isinstance(part, dict) else str(part) for part in content
            )
        return str(content)

    return _invoke


def _build_generation_prompt(document: PublicCorpusDocument, *, max_questions_per_doc: int) -> str:
    return (
        "You generate benchmark question candidates from public reference text. "
        "Return only valid JSON: an array of objects with keys "
        "question, domain, difficulty, expected_answer_points, required_sources, disallowed_behaviors. "
        f"Generate exactly {max_questions_per_doc} candidates with grounded, verifiable prompts.\n\n"
        f"Document ID: {document.id}\n"
        f"Title: {document.title}\n"
        f"URL: {document.url or 'n/a'}\n"
        f"Article:\n{document.article}"
    )


def _candidate_id(source_id: str, question: str, difficulty: str) -> str:
    digest = hashlib.sha1(f"{source_id}|{question}|{difficulty}".encode("utf-8")).hexdigest()
    return f"cand-{digest[:16]}"


def generate_candidates_from_corpus(
    corpus_path: Path,
    output_path: Path,
    *,
    model: str = "gpt-4.1-mini",
    prompt_version: str = "v1",
    max_questions_per_doc: int = 2,
    invoke_model: Callable[[str], str] | None = None,
) -> list[GeneratedQuestionCandidate]:
    """Generate candidate questions from a corpus JSONL file into review queue JSONL."""

    logger.info(
        "Starting candidate generation corpus_path=%s output_path=%s model=%s prompt_version=%s",
        corpus_path,
        output_path,
        model,
        prompt_version,
    )

    model_invoker = invoke_model or _default_model_invoker(model)

    candidates: list[GeneratedQuestionCandidate] = []
    with corpus_path.open("r", encoding="utf-8") as handle:
        for line_no, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if not line:
                continue

            document = PublicCorpusDocument.model_validate_json(line)
            prompt = _build_generation_prompt(document, max_questions_per_doc=max_questions_per_doc)
            raw_output = model_invoker(prompt)

            try:
                generated = json.loads(raw_output)
            except json.JSONDecodeError as exc:
                logger.error(
                    "Model returned invalid JSON for source_id=%s line=%s error=%s",
                    document.id,
                    line_no,
                    exc,
                )
                raise ValueError(f"Model returned invalid JSON for source_id={document.id}") from exc

            if not isinstance(generated, list):
                raise ValueError(f"Model output must be a JSON array for source_id={document.id}")

            line_count = 0
            for item in generated:
                draft = QuestionCandidateDraft.model_validate(item)
                candidate = GeneratedQuestionCandidate(
                    candidate_id=_candidate_id(document.id, draft.question, draft.difficulty),
                    source_id=document.id,
                    source_title=document.title,
                    source_url=document.url,
                    generator_model=model,
                    generation_prompt_version=prompt_version,
                    **draft.model_dump(),
                )
                candidates.append(candidate)
                line_count += 1

            logger.info(
                "Generated candidate batch source_id=%s generated_count=%s",
                document.id,
                line_count,
            )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for candidate in candidates:
            handle.write(json.dumps(candidate.model_dump(), ensure_ascii=True) + "\n")

    logger.info(
        "Completed candidate generation output_path=%s candidate_count=%s",
        output_path,
        len(candidates),
    )
    return candidates


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate benchmark question candidates from a corpus.")
    parser.add_argument("--corpus", type=Path, required=True, help="Input public corpus JSONL path")
    parser.add_argument("--output", type=Path, required=True, help="Output review queue JSONL path")
    parser.add_argument("--model", type=str, default="gpt-4.1-mini")
    parser.add_argument("--prompt-version", type=str, default="v1")
    parser.add_argument("--max-questions-per-doc", type=int, default=2)
    return parser


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO)
    args = _build_parser().parse_args(argv)
    generate_candidates_from_corpus(
        corpus_path=args.corpus,
        output_path=args.output,
        model=args.model,
        prompt_version=args.prompt_version,
        max_questions_per_doc=args.max_questions_per_doc,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
