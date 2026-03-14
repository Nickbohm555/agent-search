import logging
import sys
from pathlib import Path
from uuid import uuid4

from langchain_core.documents import Document

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from db import DATABASE_URL
from services.vector_store_service import (
    CITATION_DOCUMENT_ID_METADATA_KEY,
    CITATION_SOURCE_METADATA_KEY,
    CITATION_TITLE_METADATA_KEY,
    _normalize_document_metadata,
    add_documents_to_store,
    build_initial_search_context,
    get_vector_store,
    search_documents_for_context,
)
from utils.embeddings import get_embedding_model


def test_get_vector_store_logs_created_then_existing(caplog) -> None:
    embeddings = get_embedding_model()
    collection_name = f"test_vector_store_{uuid4().hex}"

    with caplog.at_level(logging.INFO):
        first_store = get_vector_store(
            connection=DATABASE_URL,
            collection_name=collection_name,
            embeddings=embeddings,
        )
        second_store = get_vector_store(
            connection=DATABASE_URL,
            collection_name=collection_name,
            embeddings=embeddings,
        )

    assert first_store.collection_name == collection_name
    assert second_store.collection_name == collection_name
    assert "state=created" in caplog.text
    assert "state=existing" in caplog.text

    second_store.delete_collection()


def test_add_documents_to_store_returns_ids_and_persists_wiki_metadata() -> None:
    embeddings = get_embedding_model()
    collection_name = f"test_vector_add_{uuid4().hex}"
    vector_store = get_vector_store(
        connection=DATABASE_URL,
        collection_name=collection_name,
        embeddings=embeddings,
    )

    documents = [
        Document(
            page_content="The Strait of Hormuz is a strategic shipping route.",
            metadata={
                "title": "Strait of Hormuz",
                "source": "https://en.wikipedia.org/wiki/Strait_of_Hormuz",
            },
        ),
        Document(
            page_content="NATO is a political and military alliance.",
            metadata={
                "title": "NATO",
                "source": "https://en.wikipedia.org/wiki/NATO",
            },
        ),
    ]

    ids = add_documents_to_store(vector_store, documents)
    assert len(ids) == 2
    assert all(isinstance(doc_id, str) and doc_id for doc_id in ids)

    results = vector_store.similarity_search("Hormuz shipping route", k=2)
    assert results
    assert any(result.metadata.get(CITATION_TITLE_METADATA_KEY) for result in results)
    assert any(result.metadata.get(CITATION_SOURCE_METADATA_KEY) for result in results)
    assert any(result.metadata.get("wiki_page") for result in results)
    assert any(result.metadata.get("wiki_url") for result in results)
    assert any("Hormuz" in result.page_content for result in results)

    # Re-adding to the same collection should not fail and should return new ids.
    more_ids = add_documents_to_store(vector_store, documents[:1])
    assert len(more_ids) == 1
    assert more_ids[0]

    vector_store.delete_collection()


def test_normalize_document_metadata_prefers_explicit_citation_keys() -> None:
    document = Document(
        id="doc-explicit",
        page_content="Explicit metadata should survive normalization.",
        metadata={
            CITATION_TITLE_METADATA_KEY: "Explicit Title",
            CITATION_SOURCE_METADATA_KEY: "https://example.com/explicit",
            CITATION_DOCUMENT_ID_METADATA_KEY: "doc-explicit",
        },
    )

    normalized = _normalize_document_metadata(document)

    assert normalized.metadata == {
        CITATION_TITLE_METADATA_KEY: "Explicit Title",
        CITATION_SOURCE_METADATA_KEY: "https://example.com/explicit",
        CITATION_DOCUMENT_ID_METADATA_KEY: "doc-explicit",
        "topic": "Explicit Title",
        "wiki_url": "https://example.com/explicit",
        "wiki_page": "Explicit Title",
    }
    assert normalized.id == "doc-explicit"


def test_search_documents_for_context_uses_threshold_when_available() -> None:
    expected_docs = [Document(page_content="doc one", metadata={"title": "One"})]
    captured: dict[str, object] = {}

    class _FakeStore:
        def similarity_search_with_relevance_scores(self, query, k, score_threshold):
            captured["query"] = query
            captured["k"] = k
            captured["score_threshold"] = score_threshold
            return [(expected_docs[0], 0.91)]

    docs = search_documents_for_context(
        vector_store=_FakeStore(),
        query="nato policy",
        k=3,
        score_threshold=0.5,
    )

    assert len(docs) == 1
    assert docs[0].page_content == "doc one"
    assert docs[0].metadata["title"] == "One"
    assert docs[0].metadata["score"] == 0.91
    assert captured == {"query": "nato policy", "k": 3, "score_threshold": 0.5}


def test_build_initial_search_context_shapes_metadata_and_snippet() -> None:
    docs = [
        Document(
            id="abc123",
            page_content="Line 1\nLine 2",
            metadata={
                CITATION_DOCUMENT_ID_METADATA_KEY: "abc123",
                CITATION_TITLE_METADATA_KEY: "NATO",
                CITATION_SOURCE_METADATA_KEY: "https://example.com/nato",
            },
        )
    ]

    context = build_initial_search_context(docs)

    assert context == [
        {
            "rank": 1,
            "document_id": "abc123",
            "title": "NATO",
            "source": "https://example.com/nato",
            "snippet": "Line 1 Line 2",
        }
    ]
