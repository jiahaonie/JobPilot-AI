"""Model-selected Agent tool endpoint."""

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
    """Let the model choose and execute one of three registered real tools."""

    return service.run(payload.message)
