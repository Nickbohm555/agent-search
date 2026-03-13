#!/usr/bin/env python3
"""Run a health check against agent-search using the generated SDK."""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path

DEFAULT_BASE_URL = "http://localhost:8000"
REPO_ROOT = Path(__file__).resolve().parents[2]
LOCAL_SDK_PATH = REPO_ROOT / "sdk" / "python"


if str(LOCAL_SDK_PATH) not in sys.path:
    sys.path.insert(0, str(LOCAL_SDK_PATH))

try:
    import openapi_client
    from openapi_client.rest import ApiException
except ModuleNotFoundError as exc:
    raise SystemExit(
        "Unable to import the generated SDK. Expected to find "
        f"`openapi_client` under {LOCAL_SDK_PATH}."
    ) from exc


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Call /api/health using the generated Python SDK."
    )
    parser.add_argument(
        "--base-url",
        default=os.getenv("AGENT_SEARCH_BASE_URL", DEFAULT_BASE_URL),
        help=(
            "Base URL for agent-search API "
            "(default: AGENT_SEARCH_BASE_URL env var or http://localhost:8000)"
        ),
    )
    return parser.parse_args()


def normalize_base_url(base_url: str) -> str:
    return base_url.rstrip("/") or DEFAULT_BASE_URL


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s run_health: %(message)s",
    )
    args = parse_args()
    base_url = normalize_base_url(args.base_url)
    logging.info("starting health check base_url=%s", base_url)

    configuration = openapi_client.Configuration(host=base_url)

    try:
        with openapi_client.ApiClient(configuration) as api_client:
            api = openapi_client.DefaultApi(api_client)
            response = api.health_api_health_get_without_preload_content()
        payload = json.loads(response.data.decode("utf-8"))
        logging.info(
            "health check succeeded http_status=%s app_status=%s",
            response.status,
            payload.get("status"),
        )
        print(payload)
        return 0
    except ApiException as exc:
        logging.error(
            "health check failed base_url=%s status=%s reason=%s body=%s",
            base_url,
            getattr(exc, "status", "unknown"),
            getattr(exc, "reason", "unknown"),
            getattr(exc, "body", None),
        )
    except Exception as exc:
        logging.error(
            "health check failed base_url=%s error_type=%s error=%s",
            base_url,
            type(exc).__name__,
            exc,
        )
    return 1


if __name__ == "__main__":
    sys.exit(main())
