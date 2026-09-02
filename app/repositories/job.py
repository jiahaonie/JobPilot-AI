"""岗位持久化操作。"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.job import Job


class JobRepository:
    """封装岗位聚合的 SQLAlchemy 查询。"""

    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, job: Job) -> Job:
        """暂存新岗位并填充数据库生成字段。"""
        self.session.add(job)
        self.session.flush()
        return job

    def get(self, job_id: int) -> Job | None:
        """按主键查找岗位。"""
        return self.session.get(Job, job_id)

    def list(self, *, offset: int = 0, limit: int = 100) -> list[Job]:
        """按从新到旧顺序返回岗位。"""
        statement = (
            select(Job).order_by(Job.created_at.desc(), Job.id.desc()).offset(offset).limit(limit)
        )
        return list(self.session.scalars(statement))

    def delete(self, job: Job) -> None:
        """暂存岗位删除操作。"""
        self.session.delete(job)
