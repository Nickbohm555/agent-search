import logging
import sys
from pathlib import Path

from langchain_core.documents import Document

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from schemas import WikiLoadInput
from services import wiki_ingestion_service


def test_resolve_wiki_documents_returns_documents_with_metadata_and_logs(caplog, monkeypatch) -> None:
    def fake_loader(_article_query: str):
        return [
            Document(
                page_content="A" * 1200,
                metadata={
                    "source": "https://en.wikipedia.org/wiki/Geopolitics",
                    "title": "Geopolitics",
                    "language": "en",
                },
            )
        ]

    monkeypatch.setattr(wiki_ingestion_service, "_load_wikipedia_documents", fake_loader)

    with caplog.at_level(logging.INFO):
        documents = wiki_ingestion_service.resolve_wiki_documents(WikiLoadInput(source_id="geopolitics"))

    assert len(documents) == 1
    assert isinstance(documents[0], Document)
    assert documents[0].page_content == "A" * 1200
    assert documents[0].metadata["source"] == "https://en.wikipedia.org/wiki/Geopolitics"
    assert documents[0].metadata["title"] == "Geopolitics"
    assert "Resolved 1 wiki documents for source_id='geopolitics'" in caplog.text
    assert "metadata_keys=['language', 'source', 'title']" in caplog.text


def test_resolve_wiki_documents_applies_metadata_defaults(monkeypatch) -> None:
    class StubDocument:
        def __init__(self, page_content: str, metadata: dict[str, str]):
            self.page_content = page_content
            self.metadata = metadata

    def fake_loader(_article_query: str):
        return [StubDocument(page_content="B" * 1100, metadata={})]

    monkeypatch.setattr(wiki_ingestion_service, "_load_wikipedia_documents", fake_loader)
    documents = wiki_ingestion_service.resolve_wiki_documents(WikiLoadInput(source_id="nato"))

    assert len(documents) == 1
    assert isinstance(documents[0], Document)
    assert documents[0].metadata["source"] == "nato"
    assert documents[0].metadata["title"] == "NATO"
