"""岗位应用服务。"""

from sqlalchemy.orm import Session

from app.core.exceptions import (
    InvalidJobStatusTransitionError,
    JobPreparationNotReadyError,
    ResourceNotFoundError,
)
from app.models.enums import JobAnalysisStatus, JobStatus, ResumeAnalysisStatus
from app.models.job import Job
from app.models.job_analysis import JobAnalysis
from app.models.job_resume import JobResume
from app.repositories.job import JobRepository
from app.repositories.job_requirement import JobRequirementRepository
from app.repositories.job_resume import JobResumeRepository
from app.repositories.resume import ResumeRepository
from app.schemas.job import JobCreate, JobUpdate

_ALLOWED_STATUS_TRANSITIONS: dict[JobStatus, set[JobStatus]] = {
    JobStatus.PREPARING: {JobStatus.APPLIED, JobStatus.CLOSED},
    JobStatus.APPLIED: {JobStatus.CONTACTED, JobStatus.CLOSED},
    JobStatus.CONTACTED: {JobStatus.INTERVIEW, JobStatus.CLOSED},
    JobStatus.INTERVIEW: {JobStatus.CLOSED},
    JobStatus.CLOSED: set(),
}


class JobService:
    """协调岗位用例，并将事务职责从路由中分离。"""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = JobRepository(session)
        self.requirement_repository = JobRequirementRepository(session)
        self.job_resume_repository = JobResumeRepository(session)
        self.resume_repository = ResumeRepository(session)

    def create(self, payload: JobCreate) -> Job:
        """保存岗位描述。"""
        job = Job(
            **payload.model_dump(),
            status=None,
            analysis=JobAnalysis(status=JobAnalysisStatus.PENDING),
        )
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
            analysis = job.analysis
            if analysis is None:
                analysis = JobAnalysis(job_id=job.id)
                job.analysis = analysis
            analysis.status = JobAnalysisStatus.PENDING
            analysis.error_message = None
            analysis.analyzed_at = None
        self.session.commit()
        self.session.refresh(job)
        return job

    def bind_resume(self, job_id: int, resume_id: int) -> Job:
        """在投递开始前为岗位选择唯一简历。"""
        job = self.get(job_id)
        resume = self.resume_repository.get(resume_id)
        if resume is None:
            raise ResourceNotFoundError(f"Resume {resume_id} was not found")

        binding = self.job_resume_repository.get_by_job(job_id)
        if binding is not None and binding.resume_id == resume_id:
            return job
        if job.status is not None:
            raise InvalidJobStatusTransitionError(
                f"Job {job_id} resume cannot change after preparation has started"
            )
        if binding is None:
            self.job_resume_repository.add(JobResume(job_id=job_id, resume_id=resume_id))
        else:
            binding.resume_id = resume_id
        self.session.commit()
        self.session.expire(job, ["resume_binding"])
        return job

    def unbind_resume(self, job_id: int) -> None:
        """在投递开始前解除岗位与简历的绑定。"""
        job = self.get(job_id)
        binding = self.job_resume_repository.get_by_job(job_id)
        if binding is None:
            return
        if job.status is not None:
            raise InvalidJobStatusTransitionError(
                f"Job {job_id} resume cannot be unbound after preparation has started"
            )
        self.job_resume_repository.delete(binding)
        self.session.commit()

    def prepare(self, job_id: int) -> Job:
        """在岗位和绑定简历均分析完成后开始投递准备。"""
        job = self.get(job_id)
        if job.status is not None:
            if job.status is JobStatus.PREPARING:
                return job
            raise InvalidJobStatusTransitionError(f"Job {job_id} preparation has already started")
        if job.analysis_status is not JobAnalysisStatus.READY:
            raise JobPreparationNotReadyError(f"Job {job_id} analysis is {job.analysis_status}")

        binding = self.job_resume_repository.get_by_job(job_id)
        if binding is None:
            raise JobPreparationNotReadyError(f"Job {job_id} has no bound resume")
        resume = self.resume_repository.get(binding.resume_id)
        if resume is None:
            raise ResourceNotFoundError(f"Resume {binding.resume_id} was not found")
        if resume.analysis_status is not ResumeAnalysisStatus.READY:
            raise JobPreparationNotReadyError(
                f"Resume {resume.id} analysis is {resume.analysis_status}"
            )

        job.status = JobStatus.PREPARING
        self.session.commit()
        self.session.refresh(job)
        return job

    def update_status(self, job_id: int, target: JobStatus) -> Job:
        """按照受控状态机推进岗位投递阶段。"""
        job = self.get(job_id)
        current = job.status
        if current is None:
            raise InvalidJobStatusTransitionError(
                f"Job {job_id} must start preparation before status updates"
            )
        if current is target:
            return job
        if target not in _ALLOWED_STATUS_TRANSITIONS[current]:
            raise InvalidJobStatusTransitionError(
                f"Job status cannot change from {current} to {target}"
            )

        job.status = target
        self.session.commit()
        self.session.refresh(job)
        return job

    def delete(self, job_id: int) -> None:
        """删除已保存岗位。"""
        job = self.get(job_id)
        self.repository.delete(job)
        self.session.commit()
