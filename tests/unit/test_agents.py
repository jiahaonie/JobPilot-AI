"""智能体工具校验的单元测试。"""

import pytest

from app.agents.orchestrator import ToolNotFoundError, ToolRegistry
from app.agents.tools import GetJobRequirementsInput, ToolSpec
from app.schemas.agent import AgentToolDecision
from app.services.agent import AgentWorkflowService


def test_tool_registry_validates_and_executes_input() -> None:
    registry = ToolRegistry(
        [
            ToolSpec(
                name="get_job_requirements",
                description="Read structured requirements.",
                input_model=GetJobRequirementsInput,
                handler=lambda arguments: {"job_id": arguments.job_id},
            )
        ]
    )

    assert registry.execute("get_job_requirements", {"job_id": 7}) == {"job_id": 7}


def test_tool_registry_rejects_unknown_tool() -> None:
    with pytest.raises(ToolNotFoundError):
        ToolRegistry().execute("missing", {})


class SelectingLLMClient:
    def complete_structured(self, *, prompt: str, response_model: type):
        assert "get_job_requirements" in prompt
        assert response_model is AgentToolDecision
        return AgentToolDecision(
            tool_name="get_job_requirements",
            arguments={"job_id": 7},
        )


def test_agent_uses_model_selection_then_executes_validated_tool() -> None:
    registry = ToolRegistry(
        [
            ToolSpec(
                name="get_job_requirements",
                description="Read structured requirements.",
                input_model=GetJobRequirementsInput,
                handler=lambda arguments: {"job_id": arguments.job_id},
            )
        ]
    )
    service = AgentWorkflowService(client=SelectingLLMClient(), registry=registry)

    response = service.run("读取岗位 7 的要求")

    assert response.selected_tool == "get_job_requirements"
    assert response.arguments == {"job_id": 7}
    assert response.result == {"job_id": 7}
