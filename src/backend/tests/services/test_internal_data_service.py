import sys
from pathlib import Path
from types import SimpleNamespace

from langchain_core.documents import Document
from sqlalchemy import Column, Integer, MetaData, String, Table, create_engine, insert, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from schemas import InternalDataLoadRequest, WikiLoadInput
from services import internal_data_service


def _make_session() -> Session:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    metadata = MetaData()
    Table(
        "internal_documents",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("source_type", String(50), nullable=False),
        Column("source_ref", String(255), nullable=True),
        Column("title", String(255), nullable=False),
        Column("content", String, nullable=False),
    )
    metadata.create_all(engine)
    return Session(engine)


def test_load_internal_data_wiki_orchestrates_and_persists_loaded_marker(monkeypatch) -> None:
    session = _make_session()

    resolved_documents = [
        Document(
            page_content="Geopolitics content",
            metadata={
                "title": "Geopolitics",
                "source": "https://en.wikipedia.org/wiki/Geopolitics",
            },
        )
    ]
    chunked_documents = [
        Document(page_content="chunk 1", metadata={"title": "Geopolitics"}),
        Document(page_content="chunk 2", metadata={"title": "Geopolitics"}),
    ]

    captured: dict[str, object] = {}

    def fake_get_embedding_model():
        return object()

    def fake_get_vector_store(connection: str, collection_name: str, embeddings):
        captured["connection"] = connection
        captured["collection_name"] = collection_name
        captured["embeddings"] = embeddings
        return "vector-store"

    def fake_add_documents_to_store(vector_store, documents):
        captured["vector_store"] = vector_store
        captured["documents"] = documents
        return ["id-1", "id-2"]

    monkeypatch.setattr(internal_data_service, "resolve_wiki_documents", lambda _wiki: resolved_documents)
    monkeypatch.setattr(internal_data_service, "chunk_wiki_documents", lambda _docs: chunked_documents)
    monkeypatch.setattr(internal_data_service, "get_embedding_model", fake_get_embedding_model)
    monkeypatch.setattr(internal_data_service, "get_vector_store", fake_get_vector_store)
    monkeypatch.setattr(internal_data_service, "add_documents_to_store", fake_add_documents_to_store)

    response = internal_data_service.load_internal_data(
        InternalDataLoadRequest(source_type="wiki", wiki=WikiLoadInput(source_id="geopolitics")),
        session,
    )

    assert response.status == "success"
    assert response.source_type == "wiki"
    assert response.documents_loaded == 1
    assert response.chunks_created == 2
    assert captured["vector_store"] == "vector-store"
    assert captured["documents"] == chunked_documents
    assert captured["collection_name"] == "agent_search_internal_data"

    internal_documents = Table("internal_documents", MetaData(), autoload_with=session.bind)
    persisted = session.execute(
        select(
            internal_documents.c.source_type,
            internal_documents.c.source_ref,
            internal_documents.c.title,
        ),
    ).all()
    assert persisted == [("wiki", "geopolitics", "Geopolitics")]

    session.close()


def test_list_wiki_sources_with_load_state_marks_already_loaded_sources() -> None:
    session = _make_session()

    internal_documents = Table("internal_documents", MetaData(), autoload_with=session.bind)
    session.execute(
        insert(internal_documents),
        [
            {
                "source_type": "wiki",
                "source_ref": "geopolitics",
                "title": "Geopolitics",
                "content": "Geopolitics content",
            },
            {
                "source_type": "inline",
                "source_ref": "ignored",
                "title": "Inline",
                "content": "Inline content",
            },
        ],
    )
    session.commit()

    response = internal_data_service.list_wiki_sources_with_load_state(session)
    by_id = {source.source_id: source for source in response.sources}

    assert by_id["all"].already_loaded is False
    assert by_id["geopolitics"].already_loaded is True
    assert by_id["nato"].already_loaded is False

    session.close()


def test_load_internal_data_all_skips_loaded_sources_and_aggregates(monkeypatch) -> None:
    session = _make_session()

    internal_documents = Table("internal_documents", MetaData(), autoload_with=session.bind)
    session.execute(
        insert(internal_documents),
        [
            {
                "source_type": "wiki",
                "source_ref": "geopolitics",
                "title": "Geopolitics",
                "content": "Geopolitics content",
            },
        ],
    )
    session.commit()

    sources = (
        SimpleNamespace(source_id="geopolitics", label="Geopolitics", article_query="Geopolitics"),
        SimpleNamespace(source_id="nato", label="NATO", article_query="NATO"),
    )

    def fake_list_wiki_sources():
        return sources

    def fake_resolve_wiki_documents(wiki_input):
        if wiki_input.source_id == "geopolitics":
            raise AssertionError("Loaded source should be skipped for all-source load.")
        return [
            Document(
                page_content="NATO content",
                metadata={
                    "title": "NATO",
                    "source": "https://en.wikipedia.org/wiki/NATO",
                },
            )
        ]

    def fake_chunk_wiki_documents(docs):
        assert len(docs) == 1
        return [
            Document(page_content="chunk 1", metadata={"title": "NATO"}),
            Document(page_content="chunk 2", metadata={"title": "NATO"}),
        ]

    def fake_get_embedding_model():
        return object()

    def fake_get_vector_store(connection: str, collection_name: str, embeddings):
        return "vector-store"

    captured: dict[str, object] = {}

    def fake_add_documents_to_store(vector_store, documents):
        captured["vector_store"] = vector_store
        captured["documents"] = documents
        return ["id-1", "id-2"]

    monkeypatch.setattr(internal_data_service, "list_wiki_sources", fake_list_wiki_sources)
    monkeypatch.setattr(internal_data_service, "resolve_wiki_documents", fake_resolve_wiki_documents)
    monkeypatch.setattr(internal_data_service, "chunk_wiki_documents", fake_chunk_wiki_documents)
    monkeypatch.setattr(internal_data_service, "get_embedding_model", fake_get_embedding_model)
    monkeypatch.setattr(internal_data_service, "get_vector_store", fake_get_vector_store)
    monkeypatch.setattr(internal_data_service, "add_documents_to_store", fake_add_documents_to_store)

    response = internal_data_service.load_internal_data(
        InternalDataLoadRequest(source_type="wiki", wiki=WikiLoadInput(source_id="all")),
        session,
    )

    assert response.status == "success"
    assert response.source_type == "wiki"
    assert response.documents_loaded == 1
    assert response.chunks_created == 2
    assert captured["vector_store"] == "vector-store"
    assert len(captured["documents"]) == 2

    persisted = session.execute(
        select(
            internal_documents.c.source_type,
            internal_documents.c.source_ref,
            internal_documents.c.title,
        ).where(internal_documents.c.source_ref == "nato"),
    ).all()
    assert persisted == [("wiki", "nato", "NATO")]

    session.close()
