import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from services.document_validation_service import RetrievedDocument
from services.reranker_service import RerankerConfig, rerank_documents


def test_rerank_documents_orders_by_flashrank_scores(monkeypatch) -> None:
    documents = [
        RetrievedDocument(rank=1, title="General update", source="wiki://general", content="Generic overview."),
        RetrievedDocument(rank=2, title="NATO Policy Changes", source="wiki://nato", content="Policy changed in 2025."),
        RetrievedDocument(rank=3, title="Budget Notes", source="wiki://finance", content="Cost planning only."),
    ]

    class _FakeRanker:
        def rerank(self, request):
            assert request.query == "What changed in NATO policy?"
            return [
                {"id": "1", "score": 0.92},
                {"id": "0", "score": 0.65},
                {"id": "2", "score": 0.10},
            ]

    monkeypatch.setattr("services.reranker_service._build_ranker", lambda *_: _FakeRanker())

    reranked = rerank_documents(
        query="What changed in NATO policy?",
        documents=documents,
        config=RerankerConfig(enabled=True, top_n=None),
    )

    assert len(reranked) == 3
    assert reranked[0].document.title == "NATO Policy Changes"
    assert reranked[0].reranked_rank == 1
    assert reranked[0].original_rank == 2
    assert reranked[0].score == 0.92


def test_rerank_documents_honors_top_n_after_rerank(monkeypatch) -> None:
    documents = [
        RetrievedDocument(rank=1, title="A", source="wiki://a", content="a"),
        RetrievedDocument(rank=2, title="B", source="wiki://b", content="b"),
        RetrievedDocument(rank=3, title="C", source="wiki://c", content="c"),
    ]

    class _FakeRanker:
        def rerank(self, request):
            return [{"id": "2", "score": 0.9}, {"id": "1", "score": 0.7}, {"id": "0", "score": 0.2}]

    monkeypatch.setattr("services.reranker_service._build_ranker", lambda *_: _FakeRanker())

    reranked = rerank_documents(
        query="a",
        documents=documents,
        config=RerankerConfig(enabled=True, top_n=2),
    )

    assert len(reranked) == 2
    assert [entry.document.title for entry in reranked] == ["C", "B"]
    assert [entry.document.rank for entry in reranked] == [1, 2]


def test_rerank_documents_uses_deterministic_fallback_when_disabled() -> None:
    documents = [
        RetrievedDocument(rank=1, title="A", source="wiki://a", content="a"),
        RetrievedDocument(rank=2, title="B", source="wiki://b", content="b"),
        RetrievedDocument(rank=3, title="C", source="wiki://c", content="c"),
    ]

    reranked = rerank_documents(
        query="a",
        documents=documents,
        config=RerankerConfig(enabled=False, top_n=2),
    )

    assert [entry.document.title for entry in reranked] == ["A", "B"]
    assert [entry.reranked_rank for entry in reranked] == [1, 2]


def test_rerank_documents_falls_back_when_ranker_errors(monkeypatch) -> None:
    documents = [
        RetrievedDocument(rank=1, title="A", source="wiki://a", content="a"),
        RetrievedDocument(rank=2, title="B", source="wiki://b", content="b"),
    ]

    class _BrokenRanker:
        def rerank(self, request):
            raise RuntimeError("boom")

    monkeypatch.setattr("services.reranker_service._build_ranker", lambda *_: _BrokenRanker())

    reranked = rerank_documents(
        query="a",
        documents=documents,
        config=RerankerConfig(enabled=True, top_n=None),
    )

    assert [entry.document.title for entry in reranked] == ["A", "B"]
    assert [entry.original_rank for entry in reranked] == [1, 2]
