"""Persistence operations for immutable match-report snapshots."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.match_report import MatchReportRow


class MatchReportRepository:
    """Store and query historical resume-to-job matching reports."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, report: MatchReportRow) -> MatchReportRow:
        """Stage a report and populate its database-generated ID."""

        self.session.add(report)
        self.session.flush()
        return report

    def get(self, report_id: int) -> MatchReportRow | None:
        """Find one report by primary key."""

        return self.session.get(MatchReportRow, report_id)

    def list(
        self,
        *,
        job_id: int | None = None,
        resume_id: int | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> list[MatchReportRow]:
        """Return newest reports with optional job and resume filters."""

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
