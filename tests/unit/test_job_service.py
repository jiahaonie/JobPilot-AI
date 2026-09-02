"""使用隔离持久化适配器的服务层单元测试。"""

from app.core.config import Settings
from app.core.database import Database
from app.models.enums import JobAnalysisStatus
from app.schemas.job import JobCreate, JobUpdate
from app.services.job import JobService


def test_job_service_owns_use_case_and_transaction(tmp_path) -> None:
    settings = Settings(
        environment="test",
        database_url=f"sqlite:///{tmp_path / 'service.db'}",
    )
    database = Database(settings)
    database.create_all()

    try:
        with database.session() as session:
            service = JobService(session)
            created = service.create(
                JobCreate(
                    company_name="Example Co",
                    job_title="AI Engineer Intern",
                    raw_text="Build evaluation tools.",
                )
            )
            updated = service.update(created.id, JobUpdate(city="Remote"))

            assert updated.id == created.id
            assert updated.city == "Remote"
            assert updated.status is None
            assert updated.analysis_status is JobAnalysisStatus.PENDING
    finally:
        database.dispose()
