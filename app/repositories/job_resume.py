"""岗位与投递简历关联的持久化操作。"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.job_resume import JobResume


class JobResumeRepository:
    """封装第一版单岗位单简历关联查询。"""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_job(self, job_id: int) -> JobResume | None:
        """返回岗位当前绑定的简历关联。"""
        statement = select(JobResume).where(JobResume.job_id == job_id)
        return self.session.scalar(statement)

    def get_by_resume(self, resume_id: int) -> list[JobResume]:
        """返回使用指定简历的全部岗位关联。"""
        statement = select(JobResume).where(JobResume.resume_id == resume_id)
        return list(self.session.scalars(statement))

    def add(self, binding: JobResume) -> JobResume:
        """暂存新的岗位简历关联。"""
        self.session.add(binding)
        self.session.flush()
        return binding

    def delete(self, binding: JobResume) -> None:
        """暂存岗位简历关联删除。"""
        self.session.delete(binding)
