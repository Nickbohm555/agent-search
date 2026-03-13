from __future__ import annotations

import sys
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def _resolve_docs_path() -> Path | None:
    for candidate_root in Path(__file__).resolve().parents:
        docs_path = candidate_root / "docs" / "langgraph-node-io-contracts.md"
        if docs_path.exists():
            return docs_path
    return None


DOCS_PATH = _resolve_docs_path()

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from agent_search.runtime import nodes as runtime_nodes
from agent_search.runtime.node_contracts import NODE_IO_CONTRACTS, iter_node_io_contracts


def _parse_contract_table() -> list[tuple[str, str, str, str]]:
    if DOCS_PATH is None:
        pytest.skip("docs/langgraph-node-io-contracts.md is not available in this test environment")
    rows: list[tuple[str, str, str, str]] = []
    in_table = False
    for line in DOCS_PATH.read_text(encoding="utf-8").splitlines():
        if line.strip() == "| Node | Input schema | Output schema | Implementation |":
            in_table = True
            continue
        if not in_table:
            continue
        if line.strip() == "| --- | --- | --- | --- |":
            continue
        if not line.startswith("| "):
            break
        columns = [part.strip().strip("`") for part in line.strip().strip("|").split("|")]
        rows.append((columns[0], columns[1], columns[2], columns[3]))
    return rows


def test_registry_covers_every_exported_runtime_node() -> None:
    exported_implementations = {
        f"{getattr(runtime_nodes, name).__module__}.{getattr(runtime_nodes, name).__name__}"
        for name in runtime_nodes.__all__
    }

    registered_implementations = {contract.implementation for contract in iter_node_io_contracts()}

    assert registered_implementations == exported_implementations


def test_registry_iteration_order_is_stable() -> None:
    assert [contract.node_name for contract in iter_node_io_contracts()] == list(NODE_IO_CONTRACTS.keys())


def test_docs_table_matches_runtime_registry() -> None:
    documented_rows = _parse_contract_table()
    registry_rows = [
        (
            contract.node_name,
            contract.input_schema.__name__,
            contract.output_schema.__name__,
            contract.implementation,
        )
        for contract in iter_node_io_contracts()
    ]

    assert DOCS_PATH is not None
    assert documented_rows == registry_rows
