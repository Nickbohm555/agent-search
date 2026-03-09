from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func, text
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


class BenchmarkRun(Base):
    __tablename__ = "benchmark_runs"

    run_id = Column(String(128), primary_key=True)
    status = Column(String(32), nullable=False, index=True)
    dataset_id = Column(String(255), nullable=False)
    slo_snapshot = Column(JSON().with_variant(JSONB, "postgresql"), nullable=False)
    context_fingerprint = Column(String(128), nullable=False, index=True)
    corpus_hash = Column(String(128), nullable=False)
    objective_snapshot = Column(JSON().with_variant(JSONB, "postgresql"), nullable=True)
    run_metadata = Column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    error = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    modes = relationship(
        "BenchmarkRunMode",
        back_populates="run",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    results = relationship(
        "BenchmarkResult",
        back_populates="run",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class BenchmarkRunMode(Base):
    __tablename__ = "benchmark_run_modes"
    __table_args__ = (
        UniqueConstraint("run_id", "mode", name="uq_benchmark_run_modes_run_id_mode"),
    )

    id = Column(Integer, primary_key=True)
    run_id = Column(
        String(128),
        ForeignKey("benchmark_runs.run_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    mode = Column(String(64), nullable=False)
    mode_metadata = Column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    run = relationship("BenchmarkRun", back_populates="modes")


class BenchmarkResult(Base):
    __tablename__ = "benchmark_results"
    __table_args__ = (
        UniqueConstraint("run_id", "mode", "question_id", name="uq_benchmark_results_run_mode_question"),
    )

    id = Column(Integer, primary_key=True)
    run_id = Column(
        String(128),
        ForeignKey("benchmark_runs.run_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    mode = Column(String(64), nullable=False)
    question_id = Column(String(128), nullable=False)
    answer_payload = Column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=True,
    )
    citations = Column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
        server_default=text("'[]'::jsonb"),
    )
    latency_ms = Column(Integer, nullable=True)
    token_usage = Column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=True,
    )
    execution_error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    run = relationship("BenchmarkRun", back_populates="results")
