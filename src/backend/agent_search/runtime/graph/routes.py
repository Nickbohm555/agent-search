from __future__ import annotations

from collections.abc import Sequence

from langgraph.types import Send

from agent_search.runtime.graph.state import RuntimeGraphState


def route_subquestion_lanes(state: RuntimeGraphState) -> Sequence[Send]:
    return [
        Send(
            "subquestion_lane",
            {
                "main_question": state["main_question"],
                "decomposition_sub_questions": [sub_question],
                "sub_question_artifacts": [],
                "final_answer": "",
                "citation_rows_by_index": {},
                "run_metadata": state["run_metadata"],
                "sub_qa": [],
                "output": "",
                "stage_snapshots": [],
            },
        )
        for sub_question in state["decomposition_sub_questions"]
    ]


__all__ = ["route_subquestion_lanes"]
