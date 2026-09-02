"""不可变匹配报告快照的持久化操作。"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.match_report import MatchReportRow


class MatchReportRepository:
    """保存并查询历史简历岗位匹配报告。"""

    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, report: MatchReportRow) -> MatchReportRow:
        """暂存报告并填充数据库生成的编号。"""
        self.session.add(report)
        self.session.flush()
        return report

    def get(self, report_id: int) -> MatchReportRow | None:
        """按主键查找一份报告。"""
        return self.session.get(MatchReportRow, report_id)

    def list(
        self,
        *,
        job_id: int | None = None,
        resume_id: int | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> list[MatchReportRow]:
        """按可选岗位和简历条件返回最新报告。"""
        statement = select(MatchReportRow)
        if job_id is not None:
            statement = statement.where(MatchReportRow.job_id == job_id)
        if resume_id is not None:
            statement = statement.where(MatchReportRow.resume_id == resume_id)
        statement = (
            statement.order_by(
                MatchReportRow.created_at.desc(),
                MatchReportRow.id.desc(),
            )
            .offset(offset)
            .limit(limit)
        )
        return list(self.session.scalars(statement))
