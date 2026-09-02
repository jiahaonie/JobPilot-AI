"""岗位应用服务。"""

from sqlalchemy.orm import Session

from app.core.exceptions import ResourceNotFoundError
from app.models.enums import JobStatus
from app.models.job import Job
from app.repositories.job import JobRepository
from app.repositories.job_requirement import JobRequirementRepository
from app.schemas.job import JobCreate, JobUpdate


class JobService:
    """协调岗位用例，并将事务职责从路由中分离。"""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = JobRepository(session)
        self.requirement_repository = JobRequirementRepository(session)

    def create(self, payload: JobCreate) -> Job:
        """保存岗位描述。"""
        job = Job(**payload.model_dump())
        self.repository.add(job)
        self.session.commit()
        self.session.refresh(job)
        return job

    def get(self, job_id: int) -> Job:
        """返回岗位；不存在时抛出领域层未找到异常。"""
        job = self.repository.get(job_id)
        if job is None:
            raise ResourceNotFoundError(f"Job {job_id} was not found")
        return job

    def list(self, *, offset: int = 0, limit: int = 100) -> list[Job]:
        """返回数量受限的已保存岗位列表。"""
        return self.repository.list(offset=offset, limit=limit)

    def update(self, job_id: int, payload: JobUpdate) -> Job:
        """应用部分更新，并返回刷新后的岗位。"""
        job = self.get(job_id)
        changes = payload.model_dump(exclude_unset=True)
        analysis_changed = any(
            field in changes and changes[field] != getattr(job, field)
            for field in ("job_title", "raw_text")
        )
        for field, value in changes.items():
            setattr(job, field, value)
        if analysis_changed:
            self.requirement_repository.delete_by_job(job_id)
            job.status = JobStatus.PENDING_ANALYSIS
        self.session.commit()
        self.session.refresh(job)
        return job

    def delete(self, job_id: int) -> None:
        """删除已保存岗位。"""
        job = self.get(job_id)
        self.repository.delete(job)
        self.session.commit()
