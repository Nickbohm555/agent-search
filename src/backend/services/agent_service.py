from agents.factory import build_default_agent
from schemas import RuntimeAgentInfo, RuntimeAgentRunRequest, RuntimeAgentRunResponse


def get_runtime_agent_info() -> RuntimeAgentInfo:
    agent = build_default_agent()
    return RuntimeAgentInfo(name=agent.name, version=agent.version)


def run_runtime_agent(payload: RuntimeAgentRunRequest) -> RuntimeAgentRunResponse:
    agent = build_default_agent()
    output = agent.run(payload.query)
    return RuntimeAgentRunResponse(agent_name=agent.name, output=output)
