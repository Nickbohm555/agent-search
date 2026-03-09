from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

import pytest
from sqlalchemy import Column, Integer, MetaData, String, Table, delete, insert
from sqlalchemy.orm import Session

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from benchmarks.tools import load_corpus
from schemas import InternalDataLoadResponse
from tests.services.test_internal_data_service import _make_session


def _write_manifest(path: Path, rows: list[dict[str, str]]) -> Path:
    payload = {
        "corpus_id": "internal_v1",
        "version": 1,
        "source_type": "wiki",
        "sources": rows,
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _documents_table(session: Session) -> Table:
    return Table("internal_documents", MetaData(), autoload_with=session.bind)


def test_corpus_load_is_deterministic_for_repeated_reset_runs(monkeypatch, tmp_path: Path) -> None:
    session = _make_session()
    manifest_path = _write_manifest(
        tmp_path / "manifest.json",
        [
            {"source_id": "geopolitics", "label": "Geopolitics"},
            {"source_id": "nato", "label": "NATO"},
        ],
    )

    def fake_wipe_internal_data(db: Session) -> None:
        table = _documents_table(db)
        db.execute(delete(table))
        db.commit()

    def fake_load_internal_data(payload, db: Session):
        assert payload.source_type == "wiki"
        source_id = payload.wiki.source_id
        table = _documents_table(db)
        db.execute(
            insert(table),
            [
                {
                    "source_type": "wiki",
                    "source_ref": source_id,
                    "title": source_id.upper(),
                    "content": f"{source_id} deterministic corpus text",
                }
            ],
        )
        db.commit()
        return InternalDataLoadResponse(
            status="success",
            source_type="wiki",
            documents_loaded=1,
            chunks_created=2,
        )

    monkeypatch.setattr(load_corpus, "wipe_internal_data", fake_wipe_internal_data)
    monkeypatch.setattr(load_corpus, "load_internal_data", fake_load_internal_data)

    first = load_corpus.load_corpus(db=session, manifest_path=manifest_path, reset=True)
    second = load_corpus.load_corpus(db=session, manifest_path=manifest_path, reset=True)

    assert first.source_count == 2
    assert first.documents_loaded == 2
    assert first.chunks_created == 4
    assert second.documents_loaded == first.documents_loaded
    assert second.chunks_created == first.chunks_created
    assert second.manifest_hash == first.manifest_hash
    assert second.corpus_hash == first.corpus_hash

    session.close()


def test_compute_corpus_hash_scopes_to_manifest_source_ids() -> None:
    session = _make_session()
    table = _documents_table(session)
    session.execute(
        insert(table),
        [
            {
                "source_type": "wiki",
                "source_ref": "nato",
                "title": "NATO",
                "content": "alpha",
            },
            {
                "source_type": "wiki",
                "source_ref": "united_nations",
                "title": "UN",
                "content": "beta",
            },
            {
                "source_type": "wiki",
                "source_ref": "other_source",
                "title": "Other",
                "content": "gamma",
            },
        ],
    )
    session.commit()

    hash_one = load_corpus.compute_corpus_hash(session, ["nato", "united_nations"])

    session.execute(
        delete(table).where(table.c.source_ref == "other_source"),
    )
    session.execute(
        insert(table),
        [
            {
                "source_type": "wiki",
                "source_ref": "other_source",
                "title": "Other",
                "content": "changed",
            }
        ],
    )
    session.commit()

    hash_two = load_corpus.compute_corpus_hash(session, ["nato", "united_nations"])
    assert hash_one == hash_two

    session.close()


def test_manifest_validation_rejects_duplicate_source_ids(tmp_path: Path) -> None:
    manifest_path = _write_manifest(
        tmp_path / "manifest.json",
        [
            {"source_id": "nato", "label": "NATO"},
            {"source_id": "nato", "label": "NATO duplicate"},
        ],
    )

    with pytest.raises(ValueError, match="duplicate source_id"):
        load_corpus.load_corpus_manifest(manifest_path)


def test_corpus_loader_emits_visibility_logs(monkeypatch, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    session = _make_session()
    manifest_path = _write_manifest(
        tmp_path / "manifest.json",
        [{"source_id": "geopolitics", "label": "Geopolitics"}],
    )

    def fake_wipe_internal_data(db: Session) -> None:
        table = _documents_table(db)
        db.execute(delete(table))
        db.commit()

    def fake_load_internal_data(payload, db: Session):
        table = _documents_table(db)
        db.execute(
            insert(table),
            [
                {
                    "source_type": "wiki",
                    "source_ref": payload.wiki.source_id,
                    "title": "Geopolitics",
                    "content": "stable text",
                }
            ],
        )
        db.commit()
        return InternalDataLoadResponse(
            status="success",
            source_type="wiki",
            documents_loaded=1,
            chunks_created=1,
        )

    monkeypatch.setattr(load_corpus, "wipe_internal_data", fake_wipe_internal_data)
    monkeypatch.setattr(load_corpus, "load_internal_data", fake_load_internal_data)

    caplog.set_level(logging.INFO)
    load_corpus.load_corpus(db=session, manifest_path=manifest_path, reset=True)

    assert "Starting benchmark corpus load" in caplog.text
    assert "Loaded benchmark corpus source" in caplog.text
    assert "Benchmark corpus load complete" in caplog.text

    session.close()
