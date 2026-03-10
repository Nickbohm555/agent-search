from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class DecompositionPlan(BaseModel):
    """Structured output for decomposition-only LLM call."""

    sub_questions: list[str] = Field(default_factory=list, description="Atomic sub-questions for retrieval.")

    @field_validator("sub_questions", mode="before")
    @classmethod
    def _coerce_sub_questions(cls, value: object) -> list[str]:
        if value is None:
            return []
        if isinstance(value, list):
            items = value
        else:
            items = [value]
        cleaned: list[str] = []
        for item in items:
            text = str(item).strip()
            if text:
                cleaned.append(text)
        return cleaned
