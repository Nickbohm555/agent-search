from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func
from pgvector.sqlalchemy import Vector
from sqlalchemy.orm import relationship

from db import Base
from utils.embeddings import EMBEDDING_DIM


class InternalDocument(Base):
    __tablename__ = "internal_documents"

    id = Column(Integer, primary_key=True)
    source_type = Column(String(50), nullable=False)
    source_ref = Column(String(255), nullable=True)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    chunks = relationship(
        "InternalDocumentChunk",
        back_populates="document",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class InternalDocumentChunk(Base):
    __tablename__ = "internal_document_chunks"

    id = Column(Integer, primary_key=True)
    document_id = Column(
        Integer,
        ForeignKey("internal_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    embedding = Column(Vector(EMBEDDING_DIM), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    document = relationship("InternalDocument", back_populates="chunks")
