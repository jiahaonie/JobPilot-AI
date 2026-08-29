"""HTTP contracts for search, grounded QA, and Agent execution."""

from app.api.dependencies import (
    get_agent_workflow_service,
    get_grounded_qa_service,
    get_knowledge_search_service,
)
from app.schemas.agent import AgentRunResponse
from app.schemas.knowledge import (
    KnowledgeAskResponse,
    KnowledgeSearchResponse,
    KnowledgeSearchResult,
)


def _search_result() -> KnowledgeSearchResult:
    return KnowledgeSearchResult(
        chunk_id="document:7:chunk:0",
        document_id=7,
        source_name="fastapi.md",
        chunk_index=0,
        text="Depends 用于依赖注入。",
        distance=0.12,
    )


class StubSearchService:
    def search(self, *, query: str, top_k: int, max_distance: float | None):
        threshold = 0.45 if max_distance is None else max_distance
        return KnowledgeSearchResponse(
            query=query,
            max_distance=threshold,
            results=[_search_result()],
        )


class StubQAService:
    def ask(
        self,
        *,
        question: str,
        top_k: int,
        max_distance: float | None,
    ) -> KnowledgeAskResponse:
        del question, top_k, max_distance
        return KnowledgeAskResponse(
            answer="Depends 用于依赖注入。",
            refused=False,
            cited_chunk_ids=["document:7:chunk:0"],
            citations=[_search_result()],
        )


class StubAgentService:
    def run(self, message: str) -> AgentRunResponse:
        del message
        return AgentRunResponse(
            selected_tool="search_learning_material",
            arguments={"query": "FastAPI"},
            result={"results": [_search_result().model_dump(mode="json")]},
        )


def test_search_endpoint_exposes_top_k_and_distance_threshold(application, client) -> None:
    application.dependency_overrides[get_knowledge_search_service] = StubSearchService

    response = client.post(
        "/api/v1/knowledge/search",
        json={"query": " FastAPI ", "top_k": 3, "max_distance": 0.4},
    )

    assert response.status_code == 200
    assert response.json()["query"] == "FastAPI"
    assert response.json()["max_distance"] == 0.4
    assert response.json()["results"][0]["chunk_id"] == "document:7:chunk:0"


def test_ask_endpoint_returns_auditable_citations(application, client) -> None:
    application.dependency_overrides[get_grounded_qa_service] = StubQAService

    response = client.post(
        "/api/v1/ask",
        json={"question": "Depends 是什么？"},
    )

    assert response.status_code == 200
    assert response.json()["refused"] is False
    assert response.json()["cited_chunk_ids"] == ["document:7:chunk:0"]


def test_agent_endpoint_returns_model_choice_and_tool_result(application, client) -> None:
    application.dependency_overrides[get_agent_workflow_service] = StubAgentService

    response = client.post(
        "/api/v1/agent/run",
        json={"message": "帮我搜索 FastAPI 学习材料"},
    )

    assert response.status_code == 200
    assert response.json()["selected_tool"] == "search_learning_material"
    assert response.json()["result"]["results"][0]["distance"] == 0.12
