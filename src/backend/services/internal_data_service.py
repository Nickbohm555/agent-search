from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from models import InternalDocument, InternalDocumentChunk
from schemas import (
    GoogleDocsInternalDataLoadRequest,
    InternalDataLoadRequest,
    InternalDataLoadResponse,
    InternalDataRetrieveRequest,
    InternalDataRetrieveResponse,
    InternalRetrievedChunk,
    InlineInternalDataLoadRequest,
)
from utils.embeddings import chunk_text, cosine_similarity, embed_text
from utils.google_docs import (
    GoogleDocsConfigurationError,
    GoogleDocsFetchError,
    fetch_google_docs,
)


def _persist_documents(
    *,
    source_type: str,
    documents: list[tuple[str, str, str | None]],
    db: Session,
) -> tuple[int, int]:
    documents_loaded = 0
    chunks_created = 0

    for title, content, source_ref in documents:
        document = InternalDocument(
            source_type=source_type,
            source_ref=source_ref,
            title=title,
            content=content,
        )
        db.add(document)
        db.flush()

        chunks = chunk_text(content)
        if not chunks:
            chunks = [content.strip()]

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
    return documents_loaded, chunks_created


def load_internal_data(payload: InternalDataLoadRequest, db: Session) -> InternalDataLoadResponse:
    if isinstance(payload, GoogleDocsInternalDataLoadRequest):
        try:
            docs = fetch_google_docs(payload.document_ids)
        except GoogleDocsConfigurationError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except GoogleDocsFetchError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

        documents_loaded, chunks_created = _persist_documents(
            source_type="google_docs",
            documents=[(doc.title, doc.content, f"gdoc://{doc.document_id}") for doc in docs],
            db=db,
        )
        return InternalDataLoadResponse(
            status="success",
            source_type="google_docs",
            documents_loaded=documents_loaded,
            chunks_created=chunks_created,
        )

    if not isinstance(payload, InlineInternalDataLoadRequest):
        raise HTTPException(status_code=400, detail="Unsupported source_type.")
    documents_loaded, chunks_created = _persist_documents(
        source_type="inline",
        documents=[
            (document_input.title, document_input.content, document_input.source_ref)
            for document_input in payload.documents
        ],
        db=db,
    )

    return InternalDataLoadResponse(
        status="success",
        source_type="inline",
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
