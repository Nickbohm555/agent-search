from sqlalchemy import JSON, Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func, text
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
    quality_scores = relationship(
        "BenchmarkQualityScore",
        back_populates="run",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    citation_scores = relationship(
        "BenchmarkCitationScore",
        back_populates="run",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    retrieval_metrics = relationship(
        "BenchmarkRetrievalMetric",
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
    e2e_latency_ms = Column(Integer, nullable=True)
    stage_timings = Column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=True,
    )
    timing_outcome = Column(String(32), nullable=True)
    latency_ms = Column(Integer, nullable=True)
    token_usage = Column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=True,
    )
    execution_error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    run = relationship("BenchmarkRun", back_populates="results")
    quality_score = relationship(
        "BenchmarkQualityScore",
        back_populates="result",
        uselist=False,
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    citation_score = relationship(
        "BenchmarkCitationScore",
        back_populates="result",
        uselist=False,
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    retrieval_metrics = relationship(
        "BenchmarkRetrievalMetric",
        back_populates="result",
        uselist=False,
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class BenchmarkQualityScore(Base):
    __tablename__ = "benchmark_quality_scores"
    __table_args__ = (
        UniqueConstraint("run_id", "mode", "question_id", name="uq_benchmark_quality_scores_run_mode_question"),
        UniqueConstraint("result_id", name="uq_benchmark_quality_scores_result_id"),
    )

    id = Column(Integer, primary_key=True)
    run_id = Column(
        String(128),
        ForeignKey("benchmark_runs.run_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    result_id = Column(
        Integer,
        ForeignKey("benchmark_results.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    mode = Column(String(64), nullable=False)
    question_id = Column(String(128), nullable=False)
    score = Column(Float, nullable=False)
    passed = Column(Boolean, nullable=False)
    rubric_version = Column(String(32), nullable=False)
    judge_model = Column(String(128), nullable=False)
    subscores_json = Column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=True,
    )
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    run = relationship("BenchmarkRun", back_populates="quality_scores")
    result = relationship("BenchmarkResult", back_populates="quality_score")


class BenchmarkCitationScore(Base):
    __tablename__ = "benchmark_citation_scores"
    __table_args__ = (
        UniqueConstraint("run_id", "mode", "question_id", name="uq_benchmark_citation_scores_run_mode_question"),
        UniqueConstraint("result_id", name="uq_benchmark_citation_scores_result_id"),
    )

    id = Column(Integer, primary_key=True)
    run_id = Column(
        String(128),
        ForeignKey("benchmark_runs.run_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    result_id = Column(
        Integer,
        ForeignKey("benchmark_results.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    mode = Column(String(64), nullable=False)
    question_id = Column(String(128), nullable=False)
    citation_presence_rate = Column(Float, nullable=False)
    basic_support_rate = Column(Float, nullable=False)
    evaluator_version = Column(String(32), nullable=False)
    total_citation_count = Column(Integer, nullable=False)
    found_citation_count = Column(Integer, nullable=False)
    supported_citation_count = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    run = relationship("BenchmarkRun", back_populates="citation_scores")
    result = relationship("BenchmarkResult", back_populates="citation_score")
    verifications = relationship(
        "BenchmarkCitationVerification",
        back_populates="citation_score",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class BenchmarkCitationVerification(Base):
    __tablename__ = "benchmark_citation_verifications"

    id = Column(Integer, primary_key=True)
    citation_score_id = Column(
        Integer,
        ForeignKey("benchmark_citation_scores.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    run_id = Column(
        String(128),
        ForeignKey("benchmark_runs.run_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    result_id = Column(
        Integer,
        ForeignKey("benchmark_results.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    mode = Column(String(64), nullable=False)
    question_id = Column(String(128), nullable=False)
    citation_marker = Column(String(32), nullable=False)
    citation_index = Column(Integer, nullable=False)
    claim_text = Column(Text, nullable=False)
    citation_found = Column(Boolean, nullable=False)
    is_supported = Column(Boolean, nullable=False)
    support_label = Column(String(32), nullable=False)
    support_evidence = Column(Text, nullable=True)
    verification_payload = Column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=True,
    )
    verification_type = Column(String(64), nullable=False, server_default=text("'citation_support_v1'"))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    citation_score = relationship("BenchmarkCitationScore", back_populates="verifications")


class BenchmarkRetrievalMetric(Base):
    __tablename__ = "benchmark_retrieval_metrics"
    __table_args__ = (
        UniqueConstraint("run_id", "mode", "question_id", name="uq_benchmark_retrieval_metrics_run_mode_question"),
        UniqueConstraint("result_id", name="uq_benchmark_retrieval_metrics_result_id"),
    )

    id = Column(Integer, primary_key=True)
    run_id = Column(
        String(128),
        ForeignKey("benchmark_runs.run_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    result_id = Column(
        Integer,
        ForeignKey("benchmark_results.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    mode = Column(String(64), nullable=False)
    question_id = Column(String(128), nullable=False)
    recall_at_k = Column(Float, nullable=True)
    mrr = Column(Float, nullable=True)
    ndcg = Column(Float, nullable=True)
    k = Column(Integer, nullable=False, server_default=text("10"))
    retrieved_document_ids = Column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
        server_default=text("'[]'::jsonb"),
    )
    relevant_document_ids = Column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
        server_default=text("'[]'::jsonb"),
    )
    label_source = Column(String(64), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    run = relationship("BenchmarkRun", back_populates="retrieval_metrics")
    result = relationship("BenchmarkResult", back_populates="retrieval_metrics")
