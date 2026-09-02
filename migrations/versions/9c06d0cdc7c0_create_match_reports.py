"""创建匹配报告表。

Revision ID: 9c06d0cdc7c0
Revises: 0e6687b38672
Create Date: 2026-09-01 15:05:52.317027

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# 供 Alembic 使用的版本标识。
revision: str = "9c06d0cdc7c0"
down_revision: str | Sequence[str] | None = "0e6687b38672"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """升级数据库模型。"""
    # 以下命令由 Alembic 自动生成，请按需调整。
    op.create_table(
        "match_reports",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column("resume_id", sa.Integer(), nullable=False),
        sa.Column("skill_coverage_score", sa.Float(), nullable=True),
        sa.Column("required_score", sa.Float(), nullable=True),
        sa.Column("preferred_score", sa.Float(), nullable=True),
        sa.Column("score_disclaimer", sa.Text(), nullable=False),
        sa.Column("matched_skills", sa.JSON(), nullable=False),
        sa.Column("bonus_skills", sa.JSON(), nullable=False),
        sa.Column("missing_skills", sa.JSON(), nullable=False),
        sa.Column("priority_skills", sa.JSON(), nullable=False),
        sa.Column("required_skills_snapshot", sa.JSON(), nullable=False),
        sa.Column("preferred_skills_snapshot", sa.JSON(), nullable=False),
        sa.Column("resume_skills_snapshot", sa.JSON(), nullable=False),
        sa.Column("job_requirement_updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resume_analyzed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("scoring_version", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["resume_id"], ["resumes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("match_reports", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_match_reports_job_id"), ["job_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_match_reports_resume_id"), ["resume_id"], unique=False)

    # 以上为 Alembic 自动生成命令。


def downgrade() -> None:
    """降级数据库模型。"""
    # 以下命令由 Alembic 自动生成，请按需调整。
    with op.batch_alter_table("match_reports", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_match_reports_resume_id"))
        batch_op.drop_index(batch_op.f("ix_match_reports_job_id"))

    op.drop_table("match_reports")
    # 以上为 Alembic 自动生成命令。
