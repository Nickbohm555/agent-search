import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from services.document_validation_service import RetrievedDocument
from services.reranker_service import RerankerConfig, rerank_documents


def test_rerank_documents_promotes_query_relevant_document() -> None:
    documents = [
        RetrievedDocument(rank=1, title="General update", source="wiki://general", content="Generic overview."),
        RetrievedDocument(rank=2, title="NATO Policy Changes", source="wiki://nato", content="Policy changed in 2025."),
        RetrievedDocument(rank=3, title="Budget Notes", source="wiki://finance", content="Cost planning only."),
    ]

    reranked = rerank_documents(
        query="What changed in NATO policy?",
        documents=documents,
        config=RerankerConfig(top_n=None),
    )

    assert len(reranked) == 3
    assert reranked[0].document.title == "NATO Policy Changes"
    assert reranked[0].reranked_rank == 1
    assert reranked[0].original_rank == 2


def test_rerank_documents_honors_top_n() -> None:
    documents = [
        RetrievedDocument(rank=1, title="A", source="wiki://a", content="a"),
        RetrievedDocument(rank=2, title="B", source="wiki://b", content="b"),
        RetrievedDocument(rank=3, title="C", source="wiki://c", content="c"),
    ]

    reranked = rerank_documents(
        query="a",
        documents=documents,
        config=RerankerConfig(top_n=2),
    )

    assert len(reranked) == 2
    assert [entry.document.rank for entry in reranked] == [1, 2]
