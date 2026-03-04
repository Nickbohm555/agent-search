from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from db import get_db
from models import Document
from schemas import DocumentCreate, DocumentOut, SimilarityQuery

router = APIRouter(prefix="/api", tags=["search"])


@router.post("/documents", response_model=DocumentOut)
def create_document(payload: DocumentCreate, db: Session = Depends(get_db)) -> DocumentOut:
    doc = Document(title=payload.title, content=payload.content, embedding=payload.embedding)
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return DocumentOut(id=doc.id, title=doc.title, content=doc.content)


@router.post("/similarity", response_model=list[DocumentOut])
def similarity_search(payload: SimilarityQuery, db: Session = Depends(get_db)) -> list[DocumentOut]:
    stmt = text(
        """
        SELECT id, title, content
        FROM documents
        ORDER BY embedding <=> CAST(:embedding AS vector)
        LIMIT :k
        """
    )
    embedding_literal = "[" + ",".join(str(v) for v in payload.embedding) + "]"
    rows = db.execute(stmt, {"embedding": embedding_literal, "k": payload.k}).mappings().all()
    return [DocumentOut(id=row["id"], title=row["title"], content=row["content"]) for row in rows]
