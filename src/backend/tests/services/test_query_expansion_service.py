import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from services import query_expansion_service
from services.query_expansion_service import QueryExpansionConfig


def test_expand_queries_for_subquestion_includes_original_and_normalizes(monkeypatch) -> None:
    class _FakeMultiQueryRetriever:
        def generate_queries(self, question: str, run_manager):
            _ = question, run_manager
            return [
                "  what changed in VAT policy?  ",
                "",
                "VAT policy changes in 2025",
                "VAT policy changes in 2025",
                "VAT rates by region",
            ]

    monkeypatch.setattr(query_expansion_service, "_OPENAI_API_KEY", "set")
    monkeypatch.setattr(
        query_expansion_service.MultiQueryRetriever,
        "from_llm",
        lambda **_: _FakeMultiQueryRetriever(),
    )
    config = QueryExpansionConfig(
        model="test-model",
        temperature=0.0,
        max_queries=3,
        max_query_length=120,
    )

    expanded = query_expansion_service.expand_queries_for_subquestion(
        sub_question="What changed in VAT policy?",
        model=object(),
        config=config,
    )

    assert expanded == [
        "What changed in VAT policy?",
        "VAT policy changes in 2025",
        "VAT rates by region",
    ]


def test_expand_queries_for_subquestion_uses_original_when_generation_fails(monkeypatch) -> None:
    monkeypatch.setattr(query_expansion_service, "_OPENAI_API_KEY", "set")
    monkeypatch.setattr(
        query_expansion_service.MultiQueryRetriever,
        "from_llm",
        lambda **_: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    config = QueryExpansionConfig(
        model="test-model",
        temperature=0.0,
        max_queries=4,
        max_query_length=120,
    )

    expanded = query_expansion_service.expand_queries_for_subquestion(
        sub_question="What changed in VAT policy?",
        model=object(),
        config=config,
    )

    assert expanded == ["What changed in VAT policy?"]


def test_expand_queries_for_subquestion_uses_original_when_api_key_missing(monkeypatch) -> None:
    monkeypatch.setattr(query_expansion_service, "_OPENAI_API_KEY", "")
    config = QueryExpansionConfig(
        model="test-model",
        temperature=0.0,
        max_queries=4,
        max_query_length=120,
    )

    expanded = query_expansion_service.expand_queries_for_subquestion(
        sub_question="What changed in VAT policy?",
        model=None,
        config=config,
    )

    assert expanded == ["What changed in VAT policy?"]
