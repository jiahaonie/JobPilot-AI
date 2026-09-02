"""有依据的问答端点。"""

from fastapi import APIRouter, Depends

from app.api.dependencies import get_grounded_qa_service
from app.schemas.knowledge import KnowledgeAskRequest, KnowledgeAskResponse
from app.services.qa import GroundedQuestionAnsweringService

router = APIRouter(tags=["knowledge"])


@router.post("/ask", response_model=KnowledgeAskResponse)
def ask_knowledge_base(
    payload: KnowledgeAskRequest,
    service: GroundedQuestionAnsweringService = Depends(get_grounded_qa_service),
) -> KnowledgeAskResponse:
    """仅在检索知识提供可用证据时回答。"""
    return service.ask(
        question=payload.question,
        top_k=payload.top_k,
        max_distance=payload.max_distance,
    )
