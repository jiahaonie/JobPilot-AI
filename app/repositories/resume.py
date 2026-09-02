"""简历持久化操作。"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.resume import Resume


class ResumeRepository:
    """封装简历聚合的 SQLAlchemy 查询。"""

    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, resume: Resume) -> Resume:
        """暂存新简历并填充数据库生成字段。"""
        self.session.add(resume)
        self.session.flush()
        return resume

    def get(self, resume_id: int) -> Resume | None:
        """按主键查找简历。"""
        return self.session.get(Resume, resume_id)

    def list(self, *, offset: int = 0, limit: int = 100) -> list[Resume]:
        """按从新到旧顺序返回数量受限的简历。"""
        statement = (
            select(Resume)
            .order_by(Resume.created_at.desc(), Resume.id.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(self.session.scalars(statement))

    def delete(self, resume: Resume) -> None:
        """暂存简历删除操作。"""
        self.session.delete(resume)
