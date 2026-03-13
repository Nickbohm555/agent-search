from __future__ import annotations

import inspect
import sys
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from agent_search import public_api
from pydantic import ValidationError
from schemas import (
    RuntimeAgentRunAsyncCancelResponse,
    RuntimeAgentRunAsyncStartResponse,
    RuntimeAgentRunAsyncStatusResponse,
    RuntimeAgentRunResponse,
    SubQuestionAnswer,
)


def test_public_api_sync_signature_is_frozen() -> None:
    signature = inspect.signature(public_api.run)
    assert str(signature) == "(query: 'str', *, vector_store: 'Any', model: 'Any', config: 'dict[str, Any] | None' = None) -> 'RuntimeAgentRunResponse'"
    assert signature.parameters["query"].default is inspect._empty
    assert signature.parameters["vector_store"].default is inspect._empty
    assert signature.parameters["model"].default is inspect._empty


def test_public_api_async_signatures_are_frozen() -> None:
    run_async_signature = inspect.signature(public_api.run_async)
    assert str(run_async_signature) == "(query: 'str', *, vector_store: 'Any', model: 'Any', config: 'dict[str, Any] | None' = None) -> 'RuntimeAgentRunAsyncStartResponse'"

    status_signature = inspect.signature(public_api.get_run_status)
    assert str(status_signature) == "(job_id: 'str') -> 'RuntimeAgentRunAsyncStatusResponse'"

    cancel_signature = inspect.signature(public_api.cancel_run)
    assert str(cancel_signature) == "(job_id: 'str') -> 'RuntimeAgentRunAsyncCancelResponse'"


def test_public_api_return_annotations_are_runtime_models() -> None:
    annotations = inspect.get_annotations(public_api.run, eval_str=True)
    assert annotations["return"] is RuntimeAgentRunResponse

    annotations = inspect.get_annotations(public_api.run_async, eval_str=True)
    assert annotations["return"] is RuntimeAgentRunAsyncStartResponse

    annotations = inspect.get_annotations(public_api.get_run_status, eval_str=True)
    assert annotations["return"] is RuntimeAgentRunAsyncStatusResponse

    annotations = inspect.get_annotations(public_api.cancel_run, eval_str=True)
    assert annotations["return"] is RuntimeAgentRunAsyncCancelResponse


def test_runtime_agent_run_response_contract_keeps_legacy_fields_and_additive_sub_answers() -> None:
    schema = RuntimeAgentRunResponse.model_json_schema()

    assert schema["required"] == ["output"]
    assert "main_question" in schema["properties"]
    assert "sub_qa" in schema["properties"]
    assert "final_citations" in schema["properties"]
    assert "sub_answers" in schema["properties"]

    legacy_payload = {
        "output": "Final answer",
        "main_question": "Main question?",
        "sub_qa": [
            {
                "sub_question": "Sub-question?",
                "sub_answer": "Legacy answer",
            }
        ],
        "final_citations": [],
    }

    legacy_response = RuntimeAgentRunResponse.model_validate(legacy_payload)

    assert legacy_response.sub_qa == [SubQuestionAnswer(sub_question="Sub-question?", sub_answer="Legacy answer")]
    assert legacy_response.sub_answers == []

    additive_response = RuntimeAgentRunResponse.model_validate(
        {
            **legacy_payload,
            "sub_answers": [
                {
                    "sub_question": "Sub-question?",
                    "sub_answer": "Additive answer",
                }
            ],
        }
    )

    assert additive_response.sub_qa == legacy_response.sub_qa
    assert additive_response.sub_answers == [
        SubQuestionAnswer(sub_question="Sub-question?", sub_answer="Additive answer")
    ]


def test_runtime_agent_run_response_still_requires_output() -> None:
    with pytest.raises(ValidationError):
        RuntimeAgentRunResponse.model_validate(
            {
                "main_question": "Main question?",
                "sub_qa": [],
                "sub_answers": [],
                "final_citations": [],
            }
        )
