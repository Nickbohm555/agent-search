from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from models import InternalDocument, InternalDocumentChunk
from schemas import (
    InternalDataLoadRequest,
    InternalDataLoadResponse,
    InternalDataRetrieveRequest,
    InternalDataRetrieveResponse,
    InternalDocumentInput,
    InternalRetrievedChunk,
)
from services.wiki_ingestion_service import resolve_wiki_documents
from utils.chunking import split_text
from utils.embeddings import cosine_similarity, embed_text


def _persist_documents(
    *,
    source_type: str,
    documents: list[InternalDocumentInput],
    db: Session,
) -> tuple[int, int]:
    """Persist source documents and chunks for internal retrieval.

    Called by `load_internal_data` for both inline and wiki-backed inputs.
    Uses LangChain chunk splitting via `utils.chunking.split_text` (env
    configurable `INTERNAL_DATA_CHUNK_SIZE` / `INTERNAL_DATA_CHUNK_OVERLAP`)
    before embedding and chunk-row persistence.
    Returns `(documents_loaded, chunks_created)` for response observability.
    """
    documents_loaded = 0
    chunks_created = 0

    for document_input in documents:
        document = InternalDocument(
            source_type=source_type,
            source_ref=document_input.source_ref,
            title=document_input.title,
            content=document_input.content,
        )
        db.add(document)
        db.flush()

        chunks = split_text(document_input.content)
        if not chunks:
            chunks = [document_input.content.strip()]

        for index, chunk_content in enumerate(chunks):
            embedding = embed_text(chunk_content)
            chunk = InternalDocumentChunk(
                document_id=document.id,
                chunk_index=index,
                content=chunk_content,
                embedding=embedding,
            )
            db.add(chunk)
            chunks_created += 1

        documents_loaded += 1

    return documents_loaded, chunks_created


def load_internal_data(payload: InternalDataLoadRequest, db: Session) -> InternalDataLoadResponse:
    """Load internal source material and embed chunk vectors for retrieval.

    Called by `routers/internal_data.py::load_data` for `POST /api/internal-data/load`.
    Supports `inline` payload documents and deterministic `wiki` source ingestion.
    """
    if payload.source_type == "wiki":
        if payload.wiki is None:
            raise ValueError("wiki payload is required when source_type='wiki'")
        documents_to_load = resolve_wiki_documents(payload.wiki)
    else:
        documents_to_load = payload.documents or []

    documents_loaded, chunks_created = _persist_documents(
        source_type=payload.source_type,
        documents=documents_to_load,
        db=db,
    )
    db.commit()

    return InternalDataLoadResponse(
        status="success",
        source_type=payload.source_type,
        documents_loaded=documents_loaded,
        chunks_created=chunks_created,
    )


def retrieve_internal_data(
    payload: InternalDataRetrieveRequest,
    db: Session,
) -> InternalDataRetrieveResponse:
    """Retrieve top internal chunks by semantic similarity.

    Called by `routers/internal_data.py::retrieve_data` for `POST /api/internal-data/retrieve`.
    Uses pgvector database-side ranking on Postgres (`cosine_distance` ordering) with a
    deterministic in-process fallback for non-pgvector test backends.
    """
    query_embedding = embed_text(payload.query)
    dialect = db.get_bind().dialect.name

    if dialect == "postgresql":
        distance_expr = InternalDocumentChunk.embedding.cosine_distance(query_embedding)
        total_chunks_considered = (
            db.query(func.count(InternalDocumentChunk.id))
            .filter(InternalDocumentChunk.embedding.isnot(None))
            .scalar()
            or 0
        )
        rows = (
            db.query(InternalDocumentChunk, distance_expr.label("distance"))
            .join(InternalDocument, InternalDocument.id == InternalDocumentChunk.document_id)
            .filter(InternalDocumentChunk.embedding.isnot(None))
            .order_by(distance_expr.asc(), InternalDocumentChunk.id.asc())
            .limit(payload.limit)
            .all()
        )

        results = [
            InternalRetrievedChunk(
                chunk_id=chunk.id,
                document_id=chunk.document.id,
                document_title=chunk.document.title,
                source_type=chunk.document.source_type,
                source_ref=chunk.document.source_ref,
                content=chunk.content,
                score=1.0 - float(distance),
            )
            for chunk, distance in rows
        ]

        return InternalDataRetrieveResponse(
            query=payload.query,
            total_chunks_considered=total_chunks_considered,
            results=results,
        )

    candidate_chunks = (
        db.query(InternalDocumentChunk)
        .join(InternalDocument, InternalDocument.id == InternalDocumentChunk.document_id)
        .all()
    )

    scored_results: list[InternalRetrievedChunk] = []
    for chunk in candidate_chunks:
        if chunk.embedding is None:
            continue
        score = cosine_similarity(query_embedding, list(chunk.embedding))

        scored_results.append(
            InternalRetrievedChunk(
                chunk_id=chunk.id,
                document_id=chunk.document.id,
                document_title=chunk.document.title,
                source_type=chunk.document.source_type,
                source_ref=chunk.document.source_ref,
                content=chunk.content,
                score=score,
            )
        )

    scored_results.sort(key=lambda result: (result.score, -result.chunk_id), reverse=True)

    return InternalDataRetrieveResponse(
        query=payload.query,
        total_chunks_considered=len(candidate_chunks),
        results=scored_results[: payload.limit],
    )
