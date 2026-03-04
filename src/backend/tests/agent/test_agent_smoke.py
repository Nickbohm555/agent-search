import pytest

from utils.agent_pipeline import build_agent_plan


@pytest.mark.agent_eval
@pytest.mark.smoke
def test_agent_trajectory_includes_decomposition_and_tool_selection_steps():
    plan = build_agent_plan("Check our team wiki hiring rubric and get today's US CPI reading")

    assert plan.trajectory == ["decomposition", "tool_selection"]
    assert len(plan.subqueries) >= 1
    assert [event.step for event in plan.events] == ["decomposition", "tool_selection"]
