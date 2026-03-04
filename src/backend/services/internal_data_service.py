from sqlalchemy import func
from sqlalchemy.orm import Session

from models import InternalDocument, InternalDocumentChunk
from schemas import (
    InternalDataLoadRequest,
    InternalDataLoadResponse,
    InternalDataRetrieveRequest,
    InternalDataRetrieveResponse,
    InternalRetrievedChunk,
)
from utils.embeddings import chunk_text, cosine_similarity, embed_text


def load_internal_data(payload: InternalDataLoadRequest, db: Session) -> InternalDataLoadResponse:
    documents_loaded = 0
    chunks_created = 0

    for document_input in payload.documents:
        document = InternalDocument(
            source_type=payload.source_type,
            source_ref=document_input.source_ref,
            title=document_input.title,
            content=document_input.content,
        )
        db.add(document)
        db.flush()

        chunks = chunk_text(document_input.content)
        if not chunks:
            chunks = [document_input.content.strip()]

        for index, chunk_content in enumerate(chunks):
            embedding = embed_text(chunk_content)
            chunk = InternalDocumentChunk(
                document_id=document.id,
                chunk_index=index,
                content=chunk_content,
                embedding_vector=embedding,
            )
            db.add(chunk)
            chunks_created += 1

        documents_loaded += 1

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
    query_embedding = embed_text(payload.query)
    total_chunks_considered = db.query(func.count(InternalDocumentChunk.id)).scalar() or 0

    if db.bind is not None and db.bind.dialect.name == "postgresql":
        distance_expr = InternalDocumentChunk.embedding_vector.cosine_distance(query_embedding)
        rows = (
            db.query(InternalDocumentChunk, InternalDocument, distance_expr.label("distance"))
            .join(InternalDocument, InternalDocument.id == InternalDocumentChunk.document_id)
            .order_by(distance_expr.asc(), InternalDocumentChunk.id.asc())
            .limit(payload.limit)
            .all()
        )

        return InternalDataRetrieveResponse(
            query=payload.query,
            total_chunks_considered=total_chunks_considered,
            results=[
                InternalRetrievedChunk(
                    chunk_id=chunk.id,
                    document_id=document.id,
                    document_title=document.title,
                    source_type=document.source_type,
                    source_ref=document.source_ref,
                    content=chunk.content,
                    score=1.0 - float(distance),
                )
                for chunk, document, distance in rows
            ],
        )

    # Keep deterministic fallback for SQLite-backed smoke tests.
    candidate_chunks = (
        db.query(InternalDocumentChunk)
        .join(InternalDocument, InternalDocument.id == InternalDocumentChunk.document_id)
        .all()
    )
    scored_results: list[InternalRetrievedChunk] = []
    for chunk in candidate_chunks:
        score = cosine_similarity(query_embedding, list(chunk.embedding_vector))
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
        total_chunks_considered=total_chunks_considered,
        results=scored_results[: payload.limit],
    )
