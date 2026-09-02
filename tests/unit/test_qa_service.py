"""有依据问答中拒答与引用校验的单元测试。"""

import pytest

from app.core.exceptions import GroundingValidationError
from app.schemas.knowledge import (
    GroundedAnswerDraft,
    KnowledgeSearchResponse,
    KnowledgeSearchResult,
)
from app.services.qa import (
    INSUFFICIENT_EVIDENCE_ANSWER,
    GroundedQuestionAnsweringService,
)


class StubSearchService:
    def __init__(self, results: list[KnowledgeSearchResult]) -> None:
        self.results = results

    def search(self, *, query: str, top_k: int, max_distance: float | None):
        return KnowledgeSearchResponse(
            query=query,
            max_distance=0.45 if max_distance is None else max_distance,
            results=self.results,
        )


class StubLLMClient:
    def __init__(self, draft: GroundedAnswerDraft) -> None:
        self.draft = draft
        self.calls = 0

    def complete_structured(self, *, prompt: str, response_model: type):
        self.calls += 1
        assert "document:7:chunk:0" in prompt
        assert response_model is GroundedAnswerDraft
        return self.draft


def _evidence() -> KnowledgeSearchResult:
    return KnowledgeSearchResult(
        chunk_id="document:7:chunk:0",
        document_id=7,
        source_name="fastapi.md",
        chunk_index=0,
        text="Depends 用于声明依赖。",
        distance=0.12,
    )


def test_ask_refuses_without_evidence_and_does_not_call_llm() -> None:
    client = StubLLMClient(GroundedAnswerDraft(answer="unused", cited_chunk_ids=["unused"]))
    service = GroundedQuestionAnsweringService(
        search_service=StubSearchService([]),
        client=client,
    )

    response = service.ask(question="Depends 是什么？", top_k=5, max_distance=None)

    assert response.refused is True
    assert response.answer == INSUFFICIENT_EVIDENCE_ANSWER
    assert response.cited_chunk_ids == []
    assert client.calls == 0


def test_ask_returns_only_validated_citations() -> None:
    client = StubLLMClient(
        GroundedAnswerDraft(
            answer="Depends 用于声明依赖。",
            cited_chunk_ids=["document:7:chunk:0", "document:7:chunk:0"],
        )
    )
    service = GroundedQuestionAnsweringService(
        search_service=StubSearchService([_evidence()]),
        client=client,
    )

    response = service.ask(question="Depends 是什么？", top_k=5, max_distance=None)

    assert response.refused is False
    assert response.cited_chunk_ids == ["document:7:chunk:0"]
    assert response.citations == [_evidence()]


def test_ask_rejects_hallucinated_chunk_id() -> None:
    client = StubLLMClient(GroundedAnswerDraft(answer="错误引用", cited_chunk_ids=["made-up"]))
    service = GroundedQuestionAnsweringService(
        search_service=StubSearchService([_evidence()]),
        client=client,
    )

    with pytest.raises(GroundingValidationError, match="outside"):
        service.ask(question="Depends 是什么？", top_k=5, max_distance=None)
