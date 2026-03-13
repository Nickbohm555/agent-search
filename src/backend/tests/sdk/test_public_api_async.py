from __future__ import annotations

import inspect
import sys
from pathlib import Path
from types import SimpleNamespace

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from agent_search import public_api
from agent_search.errors import SDKConfigurationError
from agent_search.runtime import jobs as runtime_jobs
from agent_search.runtime import runner as runtime_runner
from schemas import AgentRunStageMetadata, CitationSourceRow, GraphStageSnapshot, RuntimeAgentRunResponse, SubQuestionAnswer
from schemas import RuntimeSubquestionResumeEnvelope
from services import agent_service


class _CompatibleVectorStore:
    def similarity_search(self, query: str, k: int, filter=None) -> list[object]:
        return []


class _InlineExecutor:
    def submit(self, fn, *args, **kwargs):
        fn(*args, **kwargs)

        class _CompletedFuture:
            def result(self):
                return None

        return _CompletedFuture()


class _NoopExecutor:
    def submit(self, fn, *args, **kwargs):
        _ = fn, args, kwargs

        class _PendingFuture:
            def result(self):
                return None

        return _PendingFuture()


def test_run_async_signature_requires_query_vector_store_and_model() -> None:
    signature = inspect.signature(public_api.run_async)
    assert str(signature) == "(query: 'str', *, vector_store: 'Any', model: 'Any', config: 'dict[str, Any] | None' = None) -> 'RuntimeAgentRunAsyncStartResponse'"
    assert signature.parameters["query"].default is inspect._empty
    assert signature.parameters["vector_store"].default is inspect._empty
    assert signature.parameters["model"].default is inspect._empty


def test_run_async_returns_job_start_shape(monkeypatch) -> None:
    def fake_start_agent_run_job(payload, **kwargs):
        assert payload.query == "Show me async flow"
        assert payload.thread_id == "550e8400-e29b-41d4-a716-446655440000"
        assert "model" in kwargs
        assert "vector_store" in kwargs
        return SimpleNamespace(
            job_id="job-123",
            run_id="run-123",
            thread_id="550e8400-e29b-41d4-a716-446655440000",
            status="running",
        )

    monkeypatch.setattr(public_api, "start_agent_run_job", fake_start_agent_run_job)

    response = public_api.run_async(
        "Show me async flow",
        vector_store=_CompatibleVectorStore(),
        model=object(),
        config={"thread_id": "550e8400-e29b-41d4-a716-446655440000"},
    )

    assert response.model_dump() == {
        "job_id": "job-123",
        "run_id": "run-123",
        "thread_id": "550e8400-e29b-41d4-a716-446655440000",
        "status": "running",
    }


def test_run_async_returns_server_generated_thread_id_when_config_omits_it(monkeypatch) -> None:
    generated_thread_id = "550e8400-e29b-41d4-a716-446655440111"

    def fake_start_agent_run_job(payload, **kwargs):
        assert payload.query == "Show me async flow"
        assert payload.thread_id is None
        assert "model" in kwargs
        assert "vector_store" in kwargs
        return SimpleNamespace(
            job_id="job-456",
            run_id="run-456",
            thread_id=generated_thread_id,
            status="running",
        )

    monkeypatch.setattr(public_api, "start_agent_run_job", fake_start_agent_run_job)

    response = public_api.run_async(
        "Show me async flow",
        vector_store=_CompatibleVectorStore(),
        model=object(),
    )

    assert response.model_dump() == {
        "job_id": "job-456",
        "run_id": "run-456",
        "thread_id": generated_thread_id,
        "status": "running",
    }


def test_run_async_propagates_explicit_controls_to_job_payload(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_start_agent_run_job(payload, **kwargs):
        captured["payload"] = payload.model_dump(mode="json", exclude_none=True)
        captured["kwargs"] = kwargs
        return SimpleNamespace(
            job_id="job-controls",
            run_id="run-controls",
            thread_id="550e8400-e29b-41d4-a716-446655440211",
            status="running",
        )

    monkeypatch.setattr(public_api, "start_agent_run_job", fake_start_agent_run_job)

    response = public_api.run_async(
        "async controls query",
        vector_store=_CompatibleVectorStore(),
        model=object(),
        config={
            "thread_id": "550e8400-e29b-41d4-a716-446655440211",
            "rerank": {"enabled": False},
            "query_expansion": {"enabled": True},
            "hitl": {"enabled": True},
        },
    )

    assert response.job_id == "job-controls"
    assert captured["payload"] == {
        "query": "async controls query",
        "thread_id": "550e8400-e29b-41d4-a716-446655440211",
        "controls": {
            "rerank": {"enabled": False},
            "query_expansion": {"enabled": True},
            "hitl": {"enabled": True},
        },
    }


def test_run_async_propagates_subquestion_hitl_enablement_to_job_payload(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_start_agent_run_job(payload, **kwargs):
        captured["payload"] = payload.model_dump(mode="json", exclude_none=True)
        captured["kwargs"] = kwargs
        return SimpleNamespace(
            job_id="job-subquestion-hitl",
            run_id="run-subquestion-hitl",
            thread_id="550e8400-e29b-41d4-a716-446655440213",
            status="running",
        )

    monkeypatch.setattr(public_api, "start_agent_run_job", fake_start_agent_run_job)

    response = public_api.run_async(
        "async subquestion hitl query",
        vector_store=_CompatibleVectorStore(),
        model=object(),
        config={
            "thread_id": "550e8400-e29b-41d4-a716-446655440213",
            "hitl": {"subquestions": {"enabled": True}},
        },
    )

    assert response.job_id == "job-subquestion-hitl"
    assert captured["payload"] == {
        "query": "async subquestion hitl query",
        "thread_id": "550e8400-e29b-41d4-a716-446655440213",
        "controls": {
            "hitl": {
                "enabled": True,
                "subquestions": {"enabled": True},
            }
        },
    }


def test_run_async_preserves_omitted_controls_and_hitl_default_off(monkeypatch) -> None:
    captured_payloads: list[dict[str, object]] = []

    def fake_start_agent_run_job(payload, **kwargs):
        _ = kwargs
        captured_payloads.append(payload.model_dump(mode="json", exclude_none=True))
        return SimpleNamespace(
            job_id=f"job-{len(captured_payloads)}",
            run_id=f"run-{len(captured_payloads)}",
            thread_id="550e8400-e29b-41d4-a716-446655440212",
            status="running",
        )

    monkeypatch.setattr(public_api, "start_agent_run_job", fake_start_agent_run_job)

    omitted_response = public_api.run_async(
        "async omitted controls",
        vector_store=_CompatibleVectorStore(),
        model=object(),
    )
    explicit_default_response = public_api.run_async(
        "async explicit default hitl",
        vector_store=_CompatibleVectorStore(),
        model=object(),
        config={"hitl": {}},
    )

    assert omitted_response.job_id == "job-1"
    assert explicit_default_response.job_id == "job-2"
    assert captured_payloads == [
        {"query": "async omitted controls"},
        {
            "query": "async explicit default hitl",
            "controls": {"hitl": {"enabled": False}},
        },
    ]


def test_run_async_and_status_share_same_thread_id_for_one_run_lineage(monkeypatch) -> None:
    thread_id = "550e8400-e29b-41d4-a716-446655440001"

    monkeypatch.setattr(
        public_api,
        "start_agent_run_job",
        lambda payload, **kwargs: SimpleNamespace(
            job_id="job-789",
            run_id="run-789",
            thread_id=thread_id,
            status="running",
        ),
    )
    monkeypatch.setattr(
        public_api,
        "get_agent_run_job",
        lambda _job_id: SimpleNamespace(
            job_id="job-789",
            run_id="run-789",
            thread_id=thread_id,
            status="running",
            message="Still running.",
            stage="running",
            stages=[],
            decomposition_sub_questions=[],
            sub_question_artifacts=[],
            sub_qa=[],
            output="",
            result=None,
            error=None,
            cancel_requested=False,
            started_at=None,
            finished_at=None,
        ),
    )

    start_response = public_api.run_async(
        "Track continuity",
        vector_store=_CompatibleVectorStore(),
        model=object(),
    )
    status_response = public_api.get_run_status("job-789")

    assert start_response.thread_id == thread_id
    assert status_response.thread_id == thread_id


def test_run_async_persists_normalized_request_payload(monkeypatch) -> None:
    thread_id = "550e8400-e29b-41d4-a716-446655440091"

    monkeypatch.setattr(runtime_jobs.uuid, "uuid4", lambda: "job-persisted-request")
    monkeypatch.setattr(runtime_jobs, "_persist_job_status", lambda _job: None)
    monkeypatch.setattr(runtime_jobs, "_EXECUTOR", _NoopExecutor())

    response = public_api.run_async(
        "Persist the normalized request",
        vector_store=_CompatibleVectorStore(),
        model=object(),
        config={
            "thread_id": thread_id,
            "rerank": {"enabled": False},
            "query_expansion": {"enabled": True},
            "hitl": {"enabled": True},
        },
    )

    with runtime_jobs._JOB_LOCK:
        job = runtime_jobs._JOBS["job-persisted-request"]

    assert response.job_id == "job-persisted-request"
    assert job.request_payload == {
        "query": "Persist the normalized request",
        "thread_id": thread_id,
        "controls": {
            "rerank": {"enabled": False},
            "query_expansion": {"enabled": True},
            "hitl": {"enabled": True},
        },
    }


def test_get_run_status_returns_runtime_status_shape_with_timing(monkeypatch) -> None:
    def fake_get_agent_run_job(job_id):
        assert job_id == "job-456"
        return SimpleNamespace(
            job_id="job-456",
            run_id="run-456",
            thread_id="550e8400-e29b-41d4-a716-446655440000",
            status="completed",
            message="Run completed.",
            stage="completed",
            stages=[
                AgentRunStageMetadata(
                    stage="subquestions_ready",
                    status="completed",
                    sub_question="",
                    lane_index=0,
                    lane_total=1,
                    emitted_at=123.0,
                ),
                AgentRunStageMetadata(
                    stage="synthesize",
                    status="completed",
                    sub_question="What is NATO?",
                    lane_index=1,
                    lane_total=1,
                    emitted_at=124.5,
                )
            ],
            decomposition_sub_questions=["What is NATO?"],
            sub_question_artifacts=[],
            sub_qa=[
                SubQuestionAnswer(
                    sub_question="What is NATO?",
                    sub_answer="An alliance.",
                    expanded_query="What is NATO and how is it structured?",
                    answerable=True,
                    verification_reason="grounded_in_reranked_documents",
                )
            ],
            output="NATO is an alliance. [1]",
            result=RuntimeAgentRunResponse(
                main_question="What is NATO?",
                thread_id="550e8400-e29b-41d4-a716-446655440000",
                sub_qa=[
                    SubQuestionAnswer(
                        sub_question="What is NATO?",
                        sub_answer="An alliance.",
                        expanded_query="What is NATO and how is it structured?",
                        answerable=True,
                        verification_reason="grounded_in_reranked_documents",
                    )
                ],
                output="NATO is an alliance. [1]",
                final_citations=[
                    CitationSourceRow(
                        citation_index=1,
                        rank=1,
                        title="NATO reference",
                        source="docs://nato",
                        content="NATO is a political and military alliance.",
                        document_id="doc-nato",
                        score=0.97,
                    )
                ],
            ),
            error=None,
            cancel_requested=False,
            interrupt_payload={"kind": "subquestions", "items": [{"id": "sq-1", "text": "What is NATO?"}]},
            checkpoint_id="checkpoint-456",
            started_at=100.0,
            finished_at=101.5,
        )

    monkeypatch.setattr(public_api, "get_agent_run_job", fake_get_agent_run_job)

    response = public_api.get_run_status("job-456")
    payload = response.model_dump()
    assert payload["job_id"] == "job-456"
    assert payload["run_id"] == "run-456"
    assert payload["thread_id"] == "550e8400-e29b-41d4-a716-446655440000"
    assert payload["status"] == "completed"
    assert payload["stage"] == "completed"
    assert payload["elapsed_ms"] == 1500
    assert [stage["stage"] for stage in payload["stages"]] == ["subquestions_ready", "synthesize"]
    assert payload["sub_qa"][0]["answerable"] is True
    assert payload["sub_qa"][0]["verification_reason"] == "grounded_in_reranked_documents"
    assert payload["result"]["main_question"] == "What is NATO?"
    assert payload["result"]["thread_id"] == "550e8400-e29b-41d4-a716-446655440000"
    assert payload["result"]["output"] == "NATO is an alliance. [1]"
    assert payload["result"]["final_citations"][0]["citation_index"] == 1
    assert payload["result"]["final_citations"][0]["title"] == "NATO reference"
    assert payload["interrupt_payload"] == {"kind": "subquestions", "items": [{"id": "sq-1", "text": "What is NATO?"}]}
    assert payload["checkpoint_id"] == "checkpoint-456"


def test_cancel_run_returns_success_shape(monkeypatch) -> None:
    monkeypatch.setattr(public_api, "cancel_agent_run_job", lambda _job_id: True)

    response = public_api.cancel_run("job-123")

    assert response.model_dump() == {"status": "success", "message": "Cancellation requested."}


def test_get_run_status_raises_configuration_error_for_missing_job(monkeypatch) -> None:
    monkeypatch.setattr(public_api, "get_agent_run_job", lambda _job_id: None)

    try:
        public_api.get_run_status("missing-job")
    except SDKConfigurationError as exc:
        assert str(exc) == "Job not found."
    else:
        raise AssertionError("Expected SDKConfigurationError for missing job")


def test_cancel_run_raises_configuration_error_when_not_found_or_finished(monkeypatch) -> None:
    monkeypatch.setattr(public_api, "cancel_agent_run_job", lambda _job_id: False)

    try:
        public_api.cancel_run("missing-job")
    except SDKConfigurationError as exc:
        assert str(exc) == "Job not found or already finished."
    else:
        raise AssertionError("Expected SDKConfigurationError for uncancellable job")


def test_run_async_rejects_invalid_thread_id_format(monkeypatch) -> None:
    monkeypatch.setattr(public_api, "start_agent_run_job", lambda *args, **kwargs: None)

    try:
        public_api.run_async(
            "Bad thread id",
            vector_store=_CompatibleVectorStore(),
            model=object(),
            config={"thread_id": "not-a-uuid"},
        )
    except SDKConfigurationError as exc:
        assert str(exc) == "run_async failed due to invalid SDK input or configuration."
    else:
        raise AssertionError("Expected SDKConfigurationError for invalid thread_id")


def test_run_async_cutover_blocks_legacy_orchestration(monkeypatch) -> None:
    sentinel_model = object()
    sentinel_vector_store = _CompatibleVectorStore()
    thread_id = "550e8400-e29b-41d4-a716-446655440123"
    captured: dict[str, object] = {}

    monkeypatch.setattr(runtime_jobs.uuid, "uuid4", lambda: "job-cutover")
    monkeypatch.setattr(runtime_jobs, "_persist_job_status", lambda _job: None)
    monkeypatch.setattr(runtime_jobs, "_EXECUTOR", _InlineExecutor())

    def fake_execute_runtime_graph(
        *,
        context,
        run_metadata,
        config=None,
        lifecycle_callback=None,
        snapshot_callback=None,
        emit_success_terminal_event=True,
    ):
        _ = snapshot_callback, emit_success_terminal_event
        captured["query"] = context.payload.query
        captured["payload_thread_id"] = context.payload.thread_id
        captured["vector_store"] = context.vector_store
        captured["model"] = context.model
        captured["run_thread_id"] = run_metadata.thread_id
        captured["config"] = config
        captured["lifecycle_callback"] = lifecycle_callback
        return {
            "main_question": context.payload.query,
            "decomposition_sub_questions": ["Which runtime completed the request?"],
            "sub_question_artifacts": [],
            "final_answer": "The LangGraph async runtime path completed the request.",
            "citation_rows_by_index": {},
            "run_metadata": run_metadata,
            "sub_qa": [
                SubQuestionAnswer(
                    sub_question="Which runtime completed the request?",
                    sub_answer="The LangGraph async runtime path completed the request.",
                )
            ],
            "output": "The LangGraph async runtime path completed the request.",
            "stage_snapshots": [
                GraphStageSnapshot(
                    stage="decompose",
                    status="completed",
                    decomposition_sub_questions=["Which runtime completed the request?"],
                    output="The LangGraph async runtime path completed the request.",
                )
            ],
        }

    monkeypatch.setattr(runtime_jobs, "execute_runtime_graph", fake_execute_runtime_graph)
    monkeypatch.setattr(
        runtime_jobs,
        "run_checkpointed_agent",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("checkpointed legacy orchestration should not execute")),
    )
    monkeypatch.setattr(
        runtime_runner.legacy_service,
        "run_parallel_graph_runner",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("legacy orchestration should not execute")),
    )

    with runtime_jobs._JOB_LOCK:
        runtime_jobs._JOBS.clear()

    start_response = public_api.run_async(
        "Which runtime completed the request?",
        vector_store=sentinel_vector_store,
        model=sentinel_model,
        config={"thread_id": thread_id},
    )
    status_response = public_api.get_run_status(start_response.job_id)

    assert start_response.model_dump() == {
        "job_id": "job-cutover",
        "run_id": "job-cutover",
        "thread_id": thread_id,
        "status": "success",
    }
    assert status_response.status == "success"
    assert status_response.thread_id == thread_id
    assert status_response.result is not None
    assert status_response.result.output == "The LangGraph async runtime path completed the request."
    assert captured == {
        "query": "Which runtime completed the request?",
        "payload_thread_id": thread_id,
        "vector_store": sentinel_vector_store,
        "model": sentinel_model,
        "run_thread_id": thread_id,
        "config": None,
        "lifecycle_callback": captured["lifecycle_callback"],
    }


def test_resume_run_reconstructs_full_request_payload(monkeypatch) -> None:
    thread_id = "550e8400-e29b-41d4-a716-446655440092"
    sentinel_model = object()
    sentinel_vector_store = _CompatibleVectorStore()
    captured: dict[str, object] = {}

    monkeypatch.setattr(runtime_jobs, "_persist_job_status", lambda _job: None)
    monkeypatch.setattr(runtime_jobs, "_EXECUTOR", _InlineExecutor())

    def fake_run_checkpointed_agent(*, payload, run_metadata, resume=None, **_kwargs):
        captured["payload"] = payload.model_dump(mode="json", exclude_none=True)
        captured["resume"] = resume
        return SimpleNamespace(
            status="completed",
            state={
                "main_question": payload.query,
                "decomposition_sub_questions": [],
                "sub_question_artifacts": [],
                "final_answer": "Resumed with controls intact.",
                "citation_rows_by_index": {},
                "run_metadata": run_metadata,
                "sub_qa": [],
                "output": "Resumed with controls intact.",
                "stage_snapshots": [],
            },
            response=RuntimeAgentRunResponse(
                main_question=payload.query,
                thread_id=thread_id,
                sub_qa=[],
                output="Resumed with controls intact.",
            ),
            interrupt_payload=None,
            checkpoint_id="checkpoint-2",
        )

    monkeypatch.setattr(runtime_jobs, "run_checkpointed_agent", fake_run_checkpointed_agent)

    with runtime_jobs._JOB_LOCK:
        runtime_jobs._JOBS["job-resume-controls"] = runtime_jobs.AgentRunJobStatus(
            job_id="job-resume-controls",
            run_id="job-resume-controls",
            thread_id=thread_id,
            status="paused",
            query="Resume with controls",
            request_payload={
                "query": "Resume with controls",
                "thread_id": thread_id,
                "controls": {
                    "rerank": {"enabled": False},
                    "query_expansion": {"enabled": True},
                    "hitl": {"enabled": True},
                },
            },
            message="Paused and awaiting resume input.",
            stage="paused",
            interrupt_payload={"kind": "approval", "question": "Approve resume?"},
            checkpoint_id="checkpoint-1",
            runtime_model=sentinel_model,
            runtime_vector_store=sentinel_vector_store,
        )

    resumed_status = public_api.resume_run("job-resume-controls", resume={"approved": True})

    assert resumed_status.status == "success"
    assert captured == {
        "payload": {
            "query": "Resume with controls",
            "thread_id": thread_id,
            "controls": {
                "rerank": {"enabled": False},
                "query_expansion": {"enabled": True},
                "hitl": {"enabled": True},
            },
        },
        "resume": {"approved": True},
    }


def test_resume_run_validates_typed_subquestion_decisions_before_dispatch(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_resume_agent_run_job(job_id: str, *, resume=True):
        captured["job_id"] = job_id
        captured["resume"] = resume
        return SimpleNamespace(job_id=job_id)

    monkeypatch.setattr(public_api, "resume_agent_run_job", fake_resume_agent_run_job)
    monkeypatch.setattr(
        public_api,
        "get_agent_run_job",
        lambda _job_id: SimpleNamespace(
            job_id="job-typed-resume",
            run_id="run-typed-resume",
            thread_id="550e8400-e29b-41d4-a716-446655440099",
            status="running",
            message="Resume accepted.",
            stage="resuming",
            stages=[],
            decomposition_sub_questions=[],
            sub_question_artifacts=[],
            sub_qa=[],
            output="",
            result=None,
            error=None,
            cancel_requested=False,
            interrupt_payload=None,
            checkpoint_id="checkpoint-typed",
            started_at=None,
            finished_at=None,
        ),
    )

    response = public_api.resume_run(
        "job-typed-resume",
        resume={
            "checkpoint_id": "checkpoint-typed",
            "decisions": [
                {"subquestion_id": "sq-1", "action": "approve"},
                {"subquestion_id": "sq-2", "action": "edit", "edited_text": "Edited subquestion"},
                {"subquestion_id": "sq-3", "action": "deny"},
                {"subquestion_id": "sq-4", "action": "skip"},
            ],
        },
    )

    assert response.job_id == "job-typed-resume"
    assert isinstance(captured["resume"], RuntimeSubquestionResumeEnvelope)
    assert captured == {
        "job_id": "job-typed-resume",
        "resume": RuntimeSubquestionResumeEnvelope.model_validate(
            {
                "checkpoint_id": "checkpoint-typed",
                "decisions": [
                    {"subquestion_id": "sq-1", "action": "approve"},
                    {"subquestion_id": "sq-2", "action": "edit", "edited_text": "Edited subquestion"},
                    {"subquestion_id": "sq-3", "action": "deny"},
                    {"subquestion_id": "sq-4", "action": "skip"},
                ],
            }
        ),
    }


def test_resume_run_rejects_malformed_typed_subquestion_decisions_before_dispatch(monkeypatch) -> None:
    monkeypatch.setattr(
        public_api,
        "resume_agent_run_job",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("resume dispatch should not occur")),
    )

    malformed_payloads = [
        {"checkpoint_id": "checkpoint-typed", "decisions": []},
        {
            "checkpoint_id": "checkpoint-typed",
            "decisions": [{"subquestion_id": "sq-1", "action": "edit"}],
        },
        {
            "checkpoint_id": "checkpoint-typed",
            "decisions": [{"subquestion_id": "sq-1", "action": "reject"}],
        },
        {"decisions": [{"subquestion_id": "sq-1", "action": "approve"}]},
    ]

    for resume in malformed_payloads:
        try:
            public_api.resume_run("job-malformed-typed-resume", resume=resume)
        except SDKConfigurationError as exc:
            assert str(exc) == "resume_run failed due to invalid SDK input or configuration."
        else:
            raise AssertionError("Expected SDKConfigurationError for malformed typed resume payload")
