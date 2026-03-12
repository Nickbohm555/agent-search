from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
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
    chunk_metadata = Column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=True,
    )  # e.g. {"source": "<wiki URL>", "topic": "<topic name>"}
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    document = relationship("InternalDocument", back_populates="chunks")


class RuntimeExecutionRun(Base):
    __tablename__ = "runtime_execution_runs"

    run_id = Column(String(128), primary_key=True)
    thread_id = Column(String(128), nullable=False, index=True)
    status = Column(String(32), nullable=False, server_default="pending", index=True)
    idempotency_key = Column(String(255), nullable=True, unique=True)
    started_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)
    metadata_json = Column(JSON().with_variant(JSONB, "postgresql"), nullable=False, server_default="{}")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    checkpoint_links = relationship(
        "RuntimeCheckpointLink",
        back_populates="run",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    idempotency_effects = relationship(
        "RuntimeIdempotencyEffect",
        back_populates="run",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class RuntimeCheckpointLink(Base):
    __tablename__ = "runtime_checkpoint_links"

    id = Column(Integer, primary_key=True)
    run_id = Column(
        String(128),
        ForeignKey("runtime_execution_runs.run_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    thread_id = Column(String(128), nullable=False, index=True)
    checkpoint_namespace = Column(String(255), nullable=False, server_default="", index=True)
    checkpoint_id = Column(String(255), nullable=False, index=True)
    parent_checkpoint_id = Column(String(255), nullable=True)
    checkpoint_metadata = Column(JSON().with_variant(JSONB, "postgresql"), nullable=False, server_default="{}")
    is_latest = Column(Boolean, nullable=False, server_default="true")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    run = relationship("RuntimeExecutionRun", back_populates="checkpoint_links")


class RuntimeIdempotencyEffect(Base):
    __tablename__ = "runtime_idempotency_effects"

    id = Column(Integer, primary_key=True)
    run_id = Column(
        String(128),
        ForeignKey("runtime_execution_runs.run_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    thread_id = Column(String(128), nullable=False, index=True)
    node_name = Column(String(128), nullable=False)
    effect_key = Column(String(255), nullable=False)
    effect_status = Column(String(32), nullable=False, server_default="pending", index=True)
    request_payload = Column(JSON().with_variant(JSONB, "postgresql"), nullable=False, server_default="{}")
    response_payload = Column(JSON().with_variant(JSONB, "postgresql"), nullable=False, server_default="{}")
    error_message = Column(Text, nullable=True)
    first_recorded_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    last_seen_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    run = relationship("RuntimeExecutionRun", back_populates="idempotency_effects")
