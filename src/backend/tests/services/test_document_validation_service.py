import sys
import time
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from services import document_validation_service


def test_validate_subquestion_documents_applies_relevance_source_and_year_rules() -> None:
    retrieved_output = (
        "1. title=NATO Update source=wiki://trusted content=Policy changed in 2025 with new maritime guidance.\n"
        "2. title=Sports source=wiki://trusted content=Football schedule for 2025 season.\n"
        "3. title=NATO Legacy source=wiki://untrusted content=Policy baseline from 2018."
    )
    config = document_validation_service.DocumentValidationConfig(
        min_relevance_score=0.4,
        source_allowlist=("wiki://trusted",),
        min_year=2020,
        max_year=2026,
        require_year_when_range_set=True,
        max_workers=4,
    )

    result = document_validation_service.validate_subquestion_documents(
        sub_question="What changed in NATO policy in 2025?",
        retrieved_output=retrieved_output,
        config=config,
    )

    assert result.total_documents == 3
    assert len(result.valid_documents) == 1
    assert result.valid_documents[0].title == "NATO Update"
    assert result.validation_results[1].passed is False
    assert "relevance_below_threshold" in ",".join(result.validation_results[1].rejection_reasons)
    assert result.validation_results[2].passed is False
    assert "source_not_allowlisted" in result.validation_results[2].rejection_reasons
    assert "year_out_of_range" in result.validation_results[2].rejection_reasons


def test_validate_subquestion_documents_runs_in_parallel(monkeypatch) -> None:
    docs = [
        document_validation_service.RetrievedDocument(rank=1, title="A", source="wiki://a", content="nato policy"),
        document_validation_service.RetrievedDocument(rank=2, title="B", source="wiki://a", content="nato policy"),
        document_validation_service.RetrievedDocument(rank=3, title="C", source="wiki://a", content="nato policy"),
        document_validation_service.RetrievedDocument(rank=4, title="D", source="wiki://a", content="nato policy"),
    ]
    config = document_validation_service.DocumentValidationConfig(max_workers=4)

    monkeypatch.setattr(document_validation_service, "parse_retrieved_documents", lambda _: docs)

    def fake_validate_document(*, sub_question, document, config):
        time.sleep(0.12)
        return document_validation_service.ValidatedDocumentResult(
            document=document,
            relevance_score=1.0,
            passed=True,
            rejection_reasons=(),
        )

    monkeypatch.setattr(document_validation_service, "_validate_document", fake_validate_document)

    start = time.perf_counter()
    result = document_validation_service.validate_subquestion_documents(
        sub_question="nato policy",
        retrieved_output="unused",
        config=config,
    )
    elapsed = time.perf_counter() - start

    assert result.total_documents == 4
    assert len(result.valid_documents) == 4
    assert elapsed < 0.35


def test_format_retrieved_documents_preserves_numbered_identity_contract() -> None:
    documents = [
        document_validation_service.RetrievedDocument(
            rank=4,
            title="NATO Policy Update",
            source="wiki://nato/update",
            content="Policy changed in 2025.",
        ),
        document_validation_service.RetrievedDocument(
            rank=9,
            title="NATO Readiness",
            source="wiki://nato/readiness",
            content="Readiness commitments expanded.",
        ),
    ]

    formatted = document_validation_service.format_retrieved_documents(documents)

    assert formatted.splitlines() == [
        "1. title=NATO Policy Update source=wiki://nato/update content=Policy changed in 2025.",
        "2. title=NATO Readiness source=wiki://nato/readiness content=Readiness commitments expanded.",
    ]
