import logging
import sys
from pathlib import Path

from langchain_core.documents import Document

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from tools import make_retriever_tool


class _FakeVectorStore:
    def __init__(self, results: list[Document]) -> None:
        self._results = results
        self.calls: list[dict[str, object]] = []

    def similarity_search(self, query: str, k: int, filter=None) -> list[Document]:
        self.calls.append({"query": query, "k": k, "filter": filter})
        return self._results[:k]


def test_make_retriever_tool_returns_string_and_respects_limit(caplog) -> None:
    store = _FakeVectorStore(
        results=[
            Document(page_content="First content", metadata={"title": "Alpha", "source": "wiki://alpha"}),
            Document(page_content="Second content", metadata={"title": "Beta", "source": "wiki://beta"}),
            Document(page_content="Third content", metadata={"title": "Gamma", "source": "wiki://gamma"}),
        ],
    )
    retriever_tool = make_retriever_tool(store)

    with caplog.at_level(logging.INFO):
        output = retriever_tool.invoke({"query": "strategic shipping", "limit": 2})

    assert isinstance(output, str)
    assert "1. title=Alpha source=wiki://alpha content=First content" in output
    assert "2. title=Beta source=wiki://beta content=Second content" in output
    assert "Gamma" not in output
    assert store.calls == [{"query": "strategic shipping", "k": 2, "filter": None}]
    assert "query='strategic shipping'" in caplog.text
    assert "limit=2" in caplog.text
    assert "filter=None" in caplog.text
    assert "result_count=2" in caplog.text


def test_make_retriever_tool_passes_source_filter() -> None:
    store = _FakeVectorStore(
        results=[
            Document(
                page_content="Strait of Hormuz summary",
                metadata={"title": "Strait of Hormuz", "source": "https://en.wikipedia.org/wiki/Strait_of_Hormuz"},
            )
        ],
    )
    retriever_tool = make_retriever_tool(store)

    output = retriever_tool.invoke(
        {
            "query": "hormuz",
            "limit": 10,
            "wiki_source_filter": "https://en.wikipedia.org/wiki/Strait_of_Hormuz",
        }
    )

    assert "Strait of Hormuz summary" in output
    assert store.calls == [
        {
            "query": "hormuz",
            "k": 10,
            "filter": {"source": "https://en.wikipedia.org/wiki/Strait_of_Hormuz"},
        }
    ]
