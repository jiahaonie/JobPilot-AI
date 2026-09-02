"""由模型选择 Agent 工具的端点。"""

from fastapi import APIRouter, Depends

from app.api.dependencies import get_agent_workflow_service
from app.schemas.agent import AgentRunRequest, AgentRunResponse
from app.services.agent import AgentWorkflowService

router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("/run", response_model=AgentRunResponse)
def run_agent(
    payload: AgentRunRequest,
    service: AgentWorkflowService = Depends(get_agent_workflow_service),
) -> AgentRunResponse:
    """让模型选择并执行三个已注册真实工具之一。"""
    return service.run(payload.message)
