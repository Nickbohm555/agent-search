#!/usr/bin/env python3
"""Export FastAPI OpenAPI schema to a file without starting the server."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"
LOGGER = logging.getLogger("scripts.export_openapi")
CANONICAL_OPENAPI_REL_PATH = Path("openapi.json")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export OpenAPI schema from FastAPI app.")
    parser.add_argument(
        "--output",
        default=str(CANONICAL_OPENAPI_REL_PATH),
        help=f"Output path for exported OpenAPI schema (default: {CANONICAL_OPENAPI_REL_PATH}).",
    )
    return parser.parse_args()


def _load_fastapi_app(repo_root: Path):
    backend_src = repo_root / "src" / "backend"
    if str(backend_src) not in sys.path:
        sys.path.insert(0, str(backend_src))

    from main import app  # noqa: PLC0415

    return app


def main() -> int:
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
    args = _parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    canonical_output_path = repo_root / CANONICAL_OPENAPI_REL_PATH
    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = repo_root / output_path
    if output_path != canonical_output_path:
        LOGGER.warning(
            "Non-canonical OpenAPI output path requested output=%s canonical=%s",
            output_path,
            canonical_output_path,
        )

    app = _load_fastapi_app(repo_root)
    schema = app.openapi()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    schema_paths = sorted(schema.get("paths", {}).keys())
    LOGGER.info(
        "OpenAPI export complete output=%s canonical_output=%s openapi_version=%s path_count=%d sample_paths=%s",
        output_path,
        canonical_output_path,
        schema.get("openapi", "unknown"),
        len(schema_paths),
        schema_paths[:10],
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
