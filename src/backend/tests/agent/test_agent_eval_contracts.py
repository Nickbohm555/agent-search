import pytest

from tests.fixtures.agent_cases import AGENT_EVAL_CASES
from utils.agent_pipeline import build_agent_plan


@pytest.mark.agent_eval
@pytest.mark.parametrize("case", AGENT_EVAL_CASES, ids=[case["name"] for case in AGENT_EVAL_CASES])
def test_agent_eval_case_shape(case):
    assert isinstance(case["name"], str) and case["name"]
    assert isinstance(case["goal"], str) and case["goal"]
    assert isinstance(case["checks"], list) and len(case["checks"]) > 0


@pytest.mark.agent_eval
def test_agent_outcome_contract_assigns_exactly_one_tool_per_subquery():
    plan = build_agent_plan("Find our internal docs for onboarding and find latest weather outlook in Seattle")

    assert len(plan.subqueries) >= 1
    for subquery in plan.subqueries:
        assert subquery.tool in {"internal_rag", "web_search"}
