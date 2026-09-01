"""Resume persistence model."""

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import ResumeAnalysisStatus

if TYPE_CHECKING:
    from app.models.resume_analysis import ResumeAnalysis


def utc_now() -> datetime:
    """Return a timezone-aware timestamp for application records."""

    return datetime.now(UTC)


class Resume(Base):
    """A saved resume with its extracted skill list."""

    __tablename__ = "resumes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    skills: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )
    analysis: Mapped["ResumeAnalysis | None"] = relationship(
        back_populates="resume",
        cascade="all, delete-orphan",
        uselist=False,
    )

    @property
    def analysis_status(self) -> ResumeAnalysisStatus:
        """Expose lifecycle state while treating legacy resumes as analyzed."""

        return self.analysis.status if self.analysis else ResumeAnalysisStatus.READY

    @property
    def analysis_error(self) -> str | None:
        """Return the latest safe analysis failure detail, if any."""

        return self.analysis.error_message if self.analysis else None

    @property
    def analyzed_at(self) -> datetime | None:
        """Return when skill extraction most recently succeeded."""

        return self.analysis.analyzed_at if self.analysis else self.created_at
