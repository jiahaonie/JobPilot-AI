"""Unit-level service test with an isolated persistence adapter."""

from app.core.config import Settings
from app.core.database import Database
from app.models.enums import JobStatus
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
            updated = service.update(
                created.id,
                JobUpdate(status=JobStatus.PREPARING),
            )

            assert updated.id == created.id
            assert updated.status is JobStatus.PREPARING
    finally:
        database.dispose()
