"""三个真实 Agent 工具处理器的集成测试。"""

from app.agents.handlers import build_real_tool_specs
from app.agents.orchestrator import ToolRegistry
from app.core.config import Settings
from app.core.database import Database
from app.models.job import Job
from app.models.job_requirement import JobRequirementRow
from app.models.resume import Resume
from app.schemas.knowledge import KnowledgeSearchResponse, KnowledgeSearchResult


class StubSearchService:
    def search(self, *, query: str, top_k: int, max_distance: float | None):
        return KnowledgeSearchResponse(
            query=query,
            max_distance=0.45 if max_distance is None else max_distance,
            results=[
                KnowledgeSearchResult(
                    chunk_id="document:9:chunk:0",
                    document_id=9,
                    source_name="rag.md",
                    chunk_index=0,
                    text="RAG 使用检索证据约束回答。",
                    distance=0.1,
                )
            ],
        )


def test_three_agent_handlers_call_real_persistence_and_services(tmp_path) -> None:
    database = Database(
        Settings(
            environment="test",
            database_url=f"sqlite:///{tmp_path / 'agent.db'}",
        )
    )
    database.create_all()
    try:
        with database.session() as session:
            job = Job(
                company_name="Example",
                job_title="AI Intern",
                raw_text="需要 FastAPI 和 RAG。",
            )
            resume = Resume(
                title="candidate",
                raw_text="掌握 FastAPI。",
                skills=["FastAPI"],
            )
            session.add_all([job, resume])
            session.flush()
            session.add(
                JobRequirementRow(
                    job_id=job.id,
                    job_title=job.job_title,
                    required_skills=["FastAPI", "RAG"],
                    preferred_skills=[],
                    responsibilities=["开发 API"],
                    evidence=["需要 FastAPI 和 RAG。"],
                )
            )
            session.commit()

            registry = ToolRegistry(
                build_real_tool_specs(
                    session=session,
                    search_service=StubSearchService(),
                )
            )

            requirements = registry.execute("get_job_requirements", {"job_id": job.id})
            comparison = registry.execute(
                "compare_resume_with_job",
                {"job_id": job.id, "resume_id": resume.id},
            )
            search = registry.execute(
                "search_learning_material",
                {"query": "RAG 如何约束回答", "top_k": 3},
            )

            assert requirements["required_skills"] == ["FastAPI", "RAG"]
            assert comparison["matched_skills"] == ["FastAPI"]
            assert comparison["priority_skills"][0]["skill"] == "RAG"
            assert search["results"][0]["chunk_id"] == "document:9:chunk:0"
    finally:
        database.dispose()
