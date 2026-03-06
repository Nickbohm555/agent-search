#!/usr/bin/env python3
"""Run a health check against agent-search using the generated SDK."""

from __future__ import annotations

import argparse
import logging
import os
import sys

import openapi_client
from openapi_client.rest import ApiException


DEFAULT_BASE_URL = "http://localhost:8000"


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


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s run_health: %(message)s",
    )
    args = parse_args()
    logging.info("starting health check base_url=%s", args.base_url)

    configuration = openapi_client.Configuration(host=args.base_url)

    try:
        with openapi_client.ApiClient(configuration) as api_client:
            api = openapi_client.DefaultApi(api_client)
            response = api.health_api_health_get()
        logging.info("health check succeeded status=%s", response.get("status"))
        print(response)
        return 0
    except ApiException:
        logging.exception("health check failed with API error")
    except Exception:
        logging.exception("health check failed with unexpected error")
    return 1


if __name__ == "__main__":
    sys.exit(main())
