"""基于证据的问答服务。"""

from app.core.exceptions import GroundingValidationError
from app.llm.client import StructuredLLMClient
from app.llm.prompts import build_grounded_answer_prompt
from app.schemas.knowledge import (
    GroundedAnswerDraft,
    KnowledgeAskResponse,
)
from app.services.search import KnowledgeSearchService

INSUFFICIENT_EVIDENCE_ANSWER = "知识库中没有足够证据回答这个问题。"


class GroundedQuestionAnsweringService:
    """检索证据，在上下文为空时拒答，并校验模型的每条引用。"""

    def __init__(
        self,
        *,
        search_service: KnowledgeSearchService,
        client: StructuredLLMClient,
    ) -> None:
        self.search_service = search_service
        self.client = client

    def ask(
        self,
        *,
        question: str,
        top_k: int,
        max_distance: float | None,
    ) -> KnowledgeAskResponse:
        """根据检索片段回答，或返回确定性的拒答结果。"""
        search_response = self.search_service.search(
            query=question,
            top_k=top_k,
            max_distance=max_distance,
        )
        if not search_response.results:
            return KnowledgeAskResponse(
                answer=INSUFFICIENT_EVIDENCE_ANSWER,
                refused=True,
            )

        prompt = build_grounded_answer_prompt(
            question,
            [(result.chunk_id, result.text) for result in search_response.results],
        )
        draft = self.client.complete_structured(
            prompt=prompt,
            response_model=GroundedAnswerDraft,
        )
        result_by_id = {result.chunk_id: result for result in search_response.results}
        cited_ids = list(dict.fromkeys(draft.cited_chunk_ids))
        invalid_ids = [chunk_id for chunk_id in cited_ids if chunk_id not in result_by_id]
        if invalid_ids:
            raise GroundingValidationError(
                "Model cited chunks outside the retrieved evidence: " + ", ".join(invalid_ids)
            )

        return KnowledgeAskResponse(
            answer=draft.answer,
            refused=False,
            cited_chunk_ids=cited_ids,
            citations=[result_by_id[chunk_id] for chunk_id in cited_ids],
        )
