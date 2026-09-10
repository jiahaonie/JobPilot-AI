"""四个真实 Agent 工具处理器的集成测试。"""

from datetime import UTC, datetime

from app.agents.handlers import build_real_tool_specs
from app.agents.orchestrator import ToolRegistry
from app.core.config import Settings
from app.core.database import Database
from app.models.job import Job
from app.models.job_requirement import JobRequirementRow
from app.models.match_report import MatchReportRow
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


def test_four_agent_handlers_call_real_persistence_and_services(tmp_path) -> None:
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
            session.add(
                MatchReportRow(
                    job_id=job.id,
                    resume_id=resume.id,
                    skill_coverage_score=50.0,
                    required_score=50.0,
                    preferred_score=None,
                    score_disclaimer="仅表示技能覆盖程度。",
                    matched_skills=["FastAPI"],
                    bonus_skills=[],
                    missing_skills=[{"skill": "RAG", "evidence": "需要 FastAPI 和 RAG。"}],
                    priority_skills=[{"skill": "RAG", "evidence": "需要 FastAPI 和 RAG。"}],
                    required_skills_snapshot=["FastAPI", "RAG"],
                    preferred_skills_snapshot=[],
                    resume_skills_snapshot=["FastAPI"],
                    job_requirement_updated_at=datetime.now(UTC),
                    resume_analyzed_at=datetime.now(UTC),
                    scoring_version="skill-coverage-v1",
                )
            )
            session.commit()
            report = session.query(MatchReportRow).one()

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
            plan = registry.execute(
                "create_study_plan",
                {"match_report_id": report.id},
            )

            assert requirements["required_skills"] == ["FastAPI", "RAG"]
            assert comparison["matched_skills"] == ["FastAPI"]
            assert comparison["priority_skills"][0]["skill"] == "RAG"
            assert search["results"][0]["chunk_id"] == "document:9:chunk:0"
            assert plan["match_report_id"] == report.id
            assert plan["task_count"] == 3
            assert plan["generation_method"] == "rule_v1"
    finally:
        database.dispose()
