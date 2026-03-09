from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from config import BenchmarkRuntimeSettings
from db import SessionLocal
from models import BenchmarkQualityScore, BenchmarkResult

logger = logging.getLogger(__name__)

BACKEND_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_QUALITY_PROMPT_PATH = BACKEND_ROOT / "benchmarks" / "drb" / "prompts" / "quality_judge_v1.txt"
_OPENAI_JSON_BLOCK_PATTERN = re.compile(r"```(?:json)?\s*(.*?)\s*```", flags=re.DOTALL | re.IGNORECASE)


class _JudgeResponse(BaseModel):
    score: float = Field(ge=0.0, le=1.0)
    rationale: str | None = None
    subscores: dict[str, float] | None = None


@dataclass(frozen=True)
class QualityEvaluation:
    score: float
    passed: bool
    rationale: str | None
    subscores: dict[str, float] | None
    rubric_version: str
    judge_model: str


class BenchmarkQualityService:
    """Deterministic single-judge quality scorer for benchmark results."""

    def __init__(
        self,
        *,
        session_factory: sessionmaker[Session] = SessionLocal,
        runtime_settings: BenchmarkRuntimeSettings | None = None,
        llm_factory: Any | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._runtime_settings = runtime_settings or BenchmarkRuntimeSettings.from_env()
        self._llm_factory = llm_factory

    def evaluate_and_persist(
        self,
        *,
        result_id: int,
        question_text: str,
        expected_answer_points: list[str],
        required_sources: list[str],
        run_metadata: Mapping[str, Any] | None = None,
        rubric_version: str = "v1",
        pass_threshold: float | None = None,
    ) -> BenchmarkQualityScore:
        with self._session_factory() as session:
            result = session.get(BenchmarkResult, result_id)
            if result is None:
                raise ValueError(f"Benchmark result not found for quality scoring result_id={result_id}")

            evaluation = self.evaluate(
                question_text=question_text,
                answer_payload=result.answer_payload,
                expected_answer_points=expected_answer_points,
                required_sources=required_sources,
                run_metadata=run_metadata,
                rubric_version=rubric_version,
                pass_threshold=pass_threshold,
            )
            row = session.scalar(
                select(BenchmarkQualityScore).where(
                    BenchmarkQualityScore.run_id == result.run_id,
                    BenchmarkQualityScore.mode == result.mode,
                    BenchmarkQualityScore.question_id == result.question_id,
                )
            )
            if row is None:
                row = BenchmarkQualityScore(
                    run_id=result.run_id,
                    result_id=result.id,
                    mode=result.mode,
                    question_id=result.question_id,
                )
                session.add(row)

            row.result_id = result.id
            row.score = evaluation.score
            row.passed = evaluation.passed
            row.rubric_version = evaluation.rubric_version
            row.judge_model = evaluation.judge_model
            row.subscores_json = evaluation.subscores
            session.commit()
            session.refresh(row)
            logger.info(
                "Benchmark quality persisted run_id=%s mode=%s question_id=%s score=%.4f passed=%s",
                row.run_id,
                row.mode,
                row.question_id,
                row.score,
                row.passed,
            )
            return row

    def evaluate(
        self,
        *,
        question_text: str,
        answer_payload: dict[str, Any] | None,
        expected_answer_points: list[str],
        required_sources: list[str],
        run_metadata: Mapping[str, Any] | None = None,
        rubric_version: str = "v1",
        pass_threshold: float | None = None,
    ) -> QualityEvaluation:
        normalized_threshold = (
            pass_threshold if pass_threshold is not None else self._runtime_settings.target_min_correctness
        )
        answer_text = self._extract_answer_text(answer_payload)
        prompt_template = self._resolve_prompt_template(run_metadata)
        prompt = self._build_prompt(
            prompt_template=prompt_template,
            question_text=question_text,
            answer_text=answer_text,
            expected_answer_points=expected_answer_points,
            required_sources=required_sources,
            rubric_version=rubric_version,
        )
        response_payload = self._invoke_judge(prompt)
        judge_response = self._parse_judge_response(response_payload)
        score = max(0.0, min(1.0, float(judge_response.score)))
        passed = score >= normalized_threshold
        subscores = self._normalize_subscores(judge_response.subscores)

        logger.info(
            "Benchmark quality evaluated score=%.4f passed=%s threshold=%.4f rubric_version=%s model=%s",
            score,
            passed,
            normalized_threshold,
            rubric_version,
            self._runtime_settings.judge_model,
        )
        return QualityEvaluation(
            score=score,
            passed=passed,
            rationale=judge_response.rationale,
            subscores=subscores,
            rubric_version=rubric_version,
            judge_model=self._runtime_settings.judge_model,
        )

    @staticmethod
    def _extract_answer_text(answer_payload: dict[str, Any] | None) -> str:
        if not isinstance(answer_payload, dict):
            return ""
        answer = answer_payload.get("output")
        if isinstance(answer, str):
            return answer.strip()
        return ""

    def _resolve_prompt_template(self, run_metadata: Mapping[str, Any] | None) -> str:
        template_path = self._extract_artifact_prompt_path(run_metadata) or DEFAULT_QUALITY_PROMPT_PATH
        payload = template_path.read_text(encoding="utf-8").strip()
        if not payload:
            raise ValueError(f"Quality judge prompt template is empty path={template_path}")
        return payload

    @staticmethod
    def _extract_artifact_prompt_path(run_metadata: Mapping[str, Any] | None) -> Path | None:
        if not isinstance(run_metadata, Mapping):
            return None
        artifact_versions = run_metadata.get("artifact_versions")
        if not isinstance(artifact_versions, Mapping):
            return None
        prompt_data = artifact_versions.get("prompt")
        if not isinstance(prompt_data, Mapping):
            return None
        template_path = prompt_data.get("template_path")
        if not isinstance(template_path, str) or not template_path.strip():
            return None
        resolved = Path(template_path.strip()).resolve()
        return resolved if resolved.exists() else None

    def _invoke_judge(self, prompt: str) -> str:
        if self._llm_factory is not None:
            llm = self._llm_factory(model=self._runtime_settings.judge_model, temperature=0.0)
        else:
            llm = ChatOpenAI(model=self._runtime_settings.judge_model, temperature=0.0)
        response = llm.invoke(prompt)
        content = getattr(response, "content", response)
        return str(content or "").strip()

    @staticmethod
    def _extract_json_text(raw_text: str) -> str:
        text = (raw_text or "").strip()
        if not text:
            raise ValueError("Judge returned empty response")
        match = _OPENAI_JSON_BLOCK_PATTERN.search(text)
        if match:
            return match.group(1).strip()
        return text

    def _parse_judge_response(self, raw_response: str) -> _JudgeResponse:
        parsed_text = self._extract_json_text(raw_response)
        try:
            payload = json.loads(parsed_text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Judge response was not valid JSON payload={parsed_text}") from exc
        return _JudgeResponse.model_validate(payload)

    @staticmethod
    def _normalize_subscores(subscores: dict[str, float] | None) -> dict[str, float] | None:
        if not isinstance(subscores, dict):
            return None
        normalized: dict[str, float] = {}
        for key, value in subscores.items():
            if not isinstance(key, str) or not key.strip():
                continue
            if not isinstance(value, (int, float)):
                continue
            normalized[key.strip()] = max(0.0, min(1.0, float(value)))
        return normalized or None

    @staticmethod
    def _build_prompt(
        *,
        prompt_template: str,
        question_text: str,
        answer_text: str,
        expected_answer_points: list[str],
        required_sources: list[str],
        rubric_version: str,
    ) -> str:
        payload = {
            "rubric_version": rubric_version,
            "question": question_text,
            "answer": answer_text,
            "expected_answer_points": expected_answer_points,
            "required_sources": required_sources,
        }
        return (
            f"{prompt_template}\n\n"
            "Rubric instructions:\n"
            "- Score how completely the answer covers expected_answer_points.\n"
            "- Penalize unsupported claims and missing required_sources grounding.\n"
            "- Return deterministic scoring for the same input.\n\n"
            "Return strict JSON only with this shape:\n"
            '{"score": <float_0_to_1>, "rationale": "<short_reason>", "subscores": {"coverage": <float_0_to_1>}}\n\n'
            f"Evaluation payload:\n{json.dumps(payload, ensure_ascii=True, sort_keys=True)}"
        )
