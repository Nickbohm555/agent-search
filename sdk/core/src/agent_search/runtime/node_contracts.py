from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator, Literal, Mapping

from pydantic import BaseModel

from schemas import (
    AnswerSubquestionNodeInput,
    AnswerSubquestionNodeOutput,
    DecomposeNodeInput,
    DecomposeNodeOutput,
    ExpandNodeInput,
    ExpandNodeOutput,
    RerankNodeInput,
    RerankNodeOutput,
    SearchNodeInput,
    SearchNodeOutput,
    SynthesizeFinalNodeInput,
    SynthesizeFinalNodeOutput,
)

NodeName = Literal[
    "decompose",
    "expand",
    "search",
    "rerank",
    "answer_subquestion",
    "synthesize_final",
]


@dataclass(frozen=True, slots=True)
class NodeIOContract:
    node_name: NodeName
    input_schema: type[BaseModel]
    output_schema: type[BaseModel]
    implementation: str


NODE_IO_CONTRACTS: Mapping[NodeName, NodeIOContract] = {
    "decompose": NodeIOContract(
        node_name="decompose",
        input_schema=DecomposeNodeInput,
        output_schema=DecomposeNodeOutput,
        implementation="agent_search.runtime.nodes.decompose.run_decomposition_node",
    ),
    "expand": NodeIOContract(
        node_name="expand",
        input_schema=ExpandNodeInput,
        output_schema=ExpandNodeOutput,
        implementation="agent_search.runtime.nodes.expand.run_expansion_node",
    ),
    "search": NodeIOContract(
        node_name="search",
        input_schema=SearchNodeInput,
        output_schema=SearchNodeOutput,
        implementation="agent_search.runtime.nodes.search.run_search_node",
    ),
    "rerank": NodeIOContract(
        node_name="rerank",
        input_schema=RerankNodeInput,
        output_schema=RerankNodeOutput,
        implementation="agent_search.runtime.nodes.rerank.run_rerank_node",
    ),
    "answer_subquestion": NodeIOContract(
        node_name="answer_subquestion",
        input_schema=AnswerSubquestionNodeInput,
        output_schema=AnswerSubquestionNodeOutput,
        implementation="agent_search.runtime.nodes.answer.run_answer_node",
    ),
    "synthesize_final": NodeIOContract(
        node_name="synthesize_final",
        input_schema=SynthesizeFinalNodeInput,
        output_schema=SynthesizeFinalNodeOutput,
        implementation="agent_search.runtime.nodes.synthesize.run_synthesize_node",
    ),
}


def iter_node_io_contracts() -> Iterator[NodeIOContract]:
    return iter(NODE_IO_CONTRACTS.values())


def get_node_io_contract(node_name: NodeName) -> NodeIOContract:
    return NODE_IO_CONTRACTS[node_name]


__all__ = [
    "NODE_IO_CONTRACTS",
    "NodeIOContract",
    "NodeName",
    "get_node_io_contract",
    "iter_node_io_contracts",
]
