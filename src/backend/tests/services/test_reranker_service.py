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
    monkeypatch.setattr("services.reranker_service._OPENAI_API_KEY", "")

    reranked = rerank_documents(
        query="What changed in NATO policy?",
        documents=documents,
        config=RerankerConfig(enabled=True, top_n=None, provider="flashrank"),
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
    monkeypatch.setattr("services.reranker_service._OPENAI_API_KEY", "")

    reranked = rerank_documents(
        query="a",
        documents=documents,
        config=RerankerConfig(enabled=True, top_n=2, provider="flashrank"),
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
    monkeypatch.setattr("services.reranker_service._OPENAI_API_KEY", "")

    reranked = rerank_documents(
        query="a",
        documents=documents,
        config=RerankerConfig(enabled=True, top_n=None, provider="flashrank"),
    )

    assert [entry.document.title for entry in reranked] == ["A", "B"]
    assert [entry.original_rank for entry in reranked] == [1, 2]


def test_reranker_quality_eval_improves_hit_at_1_over_non_reranked_baseline(monkeypatch) -> None:
    benchmark_cases = [
        (
            "Which team won the 2025 cup final?",
            [
                RetrievedDocument(rank=1, title="General Cup Recap", source="wiki://cup-recap", content="overview"),
                RetrievedDocument(
                    rank=2,
                    title="[GOLD] 2025 Cup Final Result",
                    source="wiki://cup-final-2025",
                    content="winner details",
                ),
            ],
            "[GOLD] 2025 Cup Final Result",
        ),
        (
            "When did the VAT increase take effect?",
            [
                RetrievedDocument(rank=1, title="VAT Draft Summary", source="wiki://vat-draft", content="draft"),
                RetrievedDocument(
                    rank=2,
                    title="[GOLD] VAT Effective Date Bulletin",
                    source="wiki://vat-effective-date",
                    content="effective date",
                ),
            ],
            "[GOLD] VAT Effective Date Bulletin",
        ),
    ]

    class _FakeRanker:
        def rerank(self, request):
            ranked = []
            for passage in request.passages:
                text = passage.get("text", "")
                score = 0.99 if "[GOLD]" in text else 0.10
                ranked.append({"id": passage["id"], "score": score})
            ranked.sort(key=lambda item: item["score"], reverse=True)
            return ranked

    monkeypatch.setattr("services.reranker_service._build_ranker", lambda *_: _FakeRanker())
    monkeypatch.setattr("services.reranker_service._OPENAI_API_KEY", "")

    baseline_hit_at_1 = 0
    reranked_hit_at_1 = 0
    for query, docs, gold_title in benchmark_cases:
        baseline = rerank_documents(
            query=query,
            documents=docs,
            config=RerankerConfig(enabled=False, top_n=1),
        )
        reranked = rerank_documents(
            query=query,
            documents=docs,
            config=RerankerConfig(enabled=True, top_n=1, provider="flashrank"),
        )
        if baseline[0].document.title == gold_title:
            baseline_hit_at_1 += 1
        if reranked[0].document.title == gold_title:
            reranked_hit_at_1 += 1

    assert baseline_hit_at_1 == 0
    assert reranked_hit_at_1 == len(benchmark_cases)


def test_reranker_quality_eval_fallback_remains_deterministic_when_ranker_returns_unmappable_ids(
    monkeypatch,
) -> None:
    documents = [
        RetrievedDocument(rank=1, title="First", source="wiki://first", content="first"),
        RetrievedDocument(rank=2, title="Second", source="wiki://second", content="second"),
        RetrievedDocument(rank=3, title="Third", source="wiki://third", content="third"),
    ]

    class _FakeRanker:
        def rerank(self, request):
            _ = request
            return [{"id": "unknown-1", "score": 0.98}, {"id": "unknown-2", "score": 0.96}]

    monkeypatch.setattr("services.reranker_service._build_ranker", lambda *_: _FakeRanker())
    monkeypatch.setattr("services.reranker_service._OPENAI_API_KEY", "")

    reranked = rerank_documents(
        query="fallback check",
        documents=documents,
        config=RerankerConfig(enabled=True, top_n=2, provider="flashrank"),
    )

    assert [entry.document.title for entry in reranked] == ["First", "Second"]
    assert [entry.original_rank for entry in reranked] == [1, 2]


def test_rerank_documents_uses_openai_provider_when_api_key_is_available(monkeypatch) -> None:
    documents = [
        RetrievedDocument(rank=1, title="General update", source="wiki://general", content="overview"),
        RetrievedDocument(rank=2, title="NATO Policy Changes", source="wiki://nato", content="policy changed"),
    ]

    def _fake_rerank_with_openai(*, query, documents, config, callbacks=None):
        assert callbacks is None
        assert query == "What changed in NATO policy?"
        assert config.openai_model_name == "gpt-4.1-mini"
        assert config.openai_temperature == 0.0
        return [(documents[1], 0.97), (documents[0], 0.12)]

    monkeypatch.setattr("services.reranker_service._OPENAI_API_KEY", "test-key")
    monkeypatch.setattr("services.reranker_service._rerank_with_openai", _fake_rerank_with_openai)

    reranked = rerank_documents(
        query="What changed in NATO policy?",
        documents=documents,
        config=RerankerConfig(enabled=True, provider="openai"),
    )

    assert [entry.document.title for entry in reranked] == ["NATO Policy Changes", "General update"]
    assert [entry.score for entry in reranked] == [0.97, 0.12]


def test_rerank_documents_openai_falls_back_to_flashrank_when_openai_fails(monkeypatch) -> None:
    documents = [
        RetrievedDocument(rank=1, title="A", source="wiki://a", content="a"),
        RetrievedDocument(rank=2, title="B", source="wiki://b", content="b"),
    ]

    def _broken_rerank_with_openai(*, query, documents, config, callbacks=None):
        _ = (query, documents, config, callbacks)
        raise RuntimeError("openai-failed")

    class _FakeRanker:
        def rerank(self, request):
            _ = request
            return [{"id": "1", "score": 0.9}, {"id": "0", "score": 0.4}]

    monkeypatch.setattr("services.reranker_service._OPENAI_API_KEY", "test-key")
    monkeypatch.setattr("services.reranker_service._rerank_with_openai", _broken_rerank_with_openai)
    monkeypatch.setattr("services.reranker_service._build_ranker", lambda *_: _FakeRanker())

    reranked = rerank_documents(
        query="a",
        documents=documents,
        config=RerankerConfig(enabled=True, provider="auto"),
    )

    assert [entry.document.title for entry in reranked] == ["B", "A"]
