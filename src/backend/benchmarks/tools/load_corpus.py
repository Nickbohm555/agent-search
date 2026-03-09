from __future__ import annotations

import argparse
import hashlib
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import Column, Integer, MetaData, String, Table, select
from sqlalchemy.orm import Session

from db import SessionLocal
from schemas import InternalDataLoadRequest, WikiLoadInput
from services.internal_data_service import load_internal_data, wipe_internal_data

logger = logging.getLogger(__name__)

DEFAULT_MANIFEST_PATH = Path(__file__).resolve().parents[1] / "corpus" / "internal_v1_manifest.json"

_metadata = MetaData()
_internal_documents = Table(
    "internal_documents",
    _metadata,
    Column("id", Integer, primary_key=True),
    Column("source_type", String(50), nullable=False),
    Column("source_ref", String(255), nullable=True),
    Column("title", String(255), nullable=False),
    Column("content", String, nullable=False),
)


class CorpusSource(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    source_id: str = Field(min_length=1)
    label: str = Field(min_length=1)


class CorpusManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    corpus_id: str = Field(min_length=1)
    version: int = Field(ge=1)
    source_type: Literal["wiki"]
    sources: list[CorpusSource] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_sources_unique(self) -> "CorpusManifest":
        source_ids = [source.source_id for source in self.sources]
        if len(source_ids) != len(set(source_ids)):
            raise ValueError("Manifest contains duplicate source_id values")
        return self


@dataclass(frozen=True)
class CorpusLoadSummary:
    corpus_id: str
    source_count: int
    documents_loaded: int
    chunks_created: int
    manifest_hash: str
    corpus_hash: str


def load_corpus_manifest(path: Path) -> CorpusManifest:
    logger.info("Loading benchmark corpus manifest path=%s", path)
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    manifest = CorpusManifest.model_validate(payload)
    logger.info(
        "Loaded benchmark corpus manifest path=%s corpus_id=%s source_count=%s",
        path,
        manifest.corpus_id,
        len(manifest.sources),
    )
    return manifest


def compute_manifest_hash(manifest: CorpusManifest) -> str:
    canonical_payload = json.dumps(manifest.model_dump(), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical_payload.encode("utf-8")).hexdigest()


def compute_corpus_hash(db: Session, source_ids: list[str]) -> str:
    sorted_source_ids = sorted(source_ids)
    rows = db.execute(
        select(
            _internal_documents.c.source_type,
            _internal_documents.c.source_ref,
            _internal_documents.c.title,
            _internal_documents.c.content,
        )
        .where(
            _internal_documents.c.source_type == "wiki",
            _internal_documents.c.source_ref.in_(sorted_source_ids),
        )
        .order_by(
            _internal_documents.c.source_ref.asc(),
            _internal_documents.c.title.asc(),
            _internal_documents.c.content.asc(),
        ),
    ).all()

    hasher = hashlib.sha256()
    hasher.update(json.dumps(sorted_source_ids, separators=(",", ":")).encode("utf-8"))
    for source_type, source_ref, title, content in rows:
        canonical_row = json.dumps(
            {
                "source_type": source_type,
                "source_ref": source_ref,
                "title": title,
                "content": content,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        hasher.update(canonical_row.encode("utf-8"))

    return hasher.hexdigest()


def load_corpus(
    db: Session,
    manifest_path: Path = DEFAULT_MANIFEST_PATH,
    *,
    reset: bool = True,
) -> CorpusLoadSummary:
    manifest = load_corpus_manifest(manifest_path)
    manifest_hash = compute_manifest_hash(manifest)

    logger.info(
        "Starting benchmark corpus load corpus_id=%s source_count=%s reset=%s manifest_hash=%s",
        manifest.corpus_id,
        len(manifest.sources),
        reset,
        manifest_hash,
    )

    if reset:
        wipe_internal_data(db)

    documents_loaded = 0
    chunks_created = 0
    for source in manifest.sources:
        response = load_internal_data(
            InternalDataLoadRequest(
                source_type=manifest.source_type,
                wiki=WikiLoadInput(source_id=source.source_id),
            ),
            db,
        )
        documents_loaded += response.documents_loaded
        chunks_created += response.chunks_created
        logger.info(
            "Loaded benchmark corpus source source_id=%s source_label=%s documents_loaded=%s chunks_created=%s",
            source.source_id,
            source.label,
            response.documents_loaded,
            response.chunks_created,
        )

    corpus_hash = compute_corpus_hash(db, [source.source_id for source in manifest.sources])
    summary = CorpusLoadSummary(
        corpus_id=manifest.corpus_id,
        source_count=len(manifest.sources),
        documents_loaded=documents_loaded,
        chunks_created=chunks_created,
        manifest_hash=manifest_hash,
        corpus_hash=corpus_hash,
    )
    logger.info(
        "Benchmark corpus load complete corpus_id=%s source_count=%s documents_loaded=%s chunks_created=%s corpus_hash=%s",
        summary.corpus_id,
        summary.source_count,
        summary.documents_loaded,
        summary.chunks_created,
        summary.corpus_hash,
    )
    return summary


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Load deterministic benchmark corpus fixture.")
    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST_PATH,
        help="Path to benchmark corpus manifest JSON",
    )
    parser.add_argument(
        "--no-reset",
        action="store_true",
        help="Do not wipe existing internal documents/chunks before loading corpus sources",
    )
    return parser


def main() -> None:
    parser = _build_arg_parser()
    args = parser.parse_args()

    with SessionLocal() as db:
        summary = load_corpus(db=db, manifest_path=args.manifest, reset=not args.no_reset)

    print(json.dumps(summary.__dict__, sort_keys=True))


if __name__ == "__main__":
    main()
