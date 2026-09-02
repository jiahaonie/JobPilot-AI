"""拆分岗位分析状态并增加岗位简历绑定。

Revision ID: 4f3d5a7b9c21
Revises: 9c06d0cdc7c0
Create Date: 2026-09-02 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "4f3d5a7b9c21"
down_revision: str | Sequence[str] | None = "9c06d0cdc7c0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_OLD_JOB_STATUS = sa.Enum(
    "pending_analysis",
    "preparing",
    "applied",
    "contacted",
    "interview",
    "closed",
    name="jobstatus",
    native_enum=False,
)
_NEW_JOB_STATUS = sa.Enum(
    "preparing",
    "applied",
    "contacted",
    "interview",
    "closed",
    name="jobstatus",
    native_enum=False,
)


def upgrade() -> None:
    """升级为独立岗位分析状态和第一版单简历绑定。"""
    connection = op.get_bind()
    active_legacy_jobs = connection.execute(
        sa.text(
            "SELECT COUNT(*) FROM jobs WHERE status IS NOT NULL AND status != 'pending_analysis'"
        )
    ).scalar_one()
    if active_legacy_jobs:
        raise RuntimeError(
            "Cannot migrate active jobs without knowing their resume_id; "
            "bind each legacy job to its real resume before upgrading"
        )

    op.create_table(
        "job_analyses",
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "pending",
                "analyzing",
                "ready",
                "failed",
                name="jobanalysisstatus",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("analyzed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("job_id"),
    )
    op.create_table(
        "job_resumes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column("resume_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["resume_id"], ["resumes.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("job_id", name="uq_job_resumes_job_id"),
        sa.UniqueConstraint("job_id", "resume_id", name="uq_job_resumes_job_resume"),
    )
    with op.batch_alter_table("job_resumes", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_job_resumes_job_id"), ["job_id"], unique=False)
        batch_op.create_index(
            batch_op.f("ix_job_resumes_resume_id"),
            ["resume_id"],
            unique=False,
        )

    connection.execute(
        sa.text(
            """
            INSERT INTO job_analyses (
                job_id,
                status,
                error_message,
                analyzed_at,
                updated_at
            )
            SELECT
                jobs.id,
                CASE WHEN job_requirements.id IS NULL THEN 'pending' ELSE 'ready' END,
                NULL,
                job_requirements.updated_at,
                jobs.updated_at
            FROM jobs
            LEFT JOIN job_requirements ON job_requirements.job_id = jobs.id
            """
        )
    )
    with op.batch_alter_table("jobs", schema=None) as batch_op:
        batch_op.alter_column(
            "status",
            existing_type=_OLD_JOB_STATUS,
            existing_nullable=False,
            nullable=True,
        )
    connection.execute(sa.text("UPDATE jobs SET status = NULL WHERE status = 'pending_analysis'"))
    with op.batch_alter_table("jobs", schema=None) as batch_op:
        batch_op.alter_column(
            "status",
            existing_type=_OLD_JOB_STATUS,
            type_=_NEW_JOB_STATUS,
            existing_nullable=True,
        )


def downgrade() -> None:
    """恢复岗位表中的旧版混合状态。"""
    connection = op.get_bind()
    with op.batch_alter_table("jobs", schema=None) as batch_op:
        batch_op.alter_column(
            "status",
            existing_type=_NEW_JOB_STATUS,
            type_=_OLD_JOB_STATUS,
            existing_nullable=True,
        )
    connection.execute(sa.text("UPDATE jobs SET status = 'pending_analysis' WHERE status IS NULL"))
    with op.batch_alter_table("jobs", schema=None) as batch_op:
        batch_op.alter_column(
            "status",
            existing_type=_OLD_JOB_STATUS,
            existing_nullable=True,
            nullable=False,
        )

    with op.batch_alter_table("job_resumes", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_job_resumes_resume_id"))
        batch_op.drop_index(batch_op.f("ix_job_resumes_job_id"))
    op.drop_table("job_resumes")
    op.drop_table("job_analyses")
