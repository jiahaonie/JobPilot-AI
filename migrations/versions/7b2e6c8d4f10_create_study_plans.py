"""创建学习计划与任务表。

Revision ID: 7b2e6c8d4f10
Revises: 4f3d5a7b9c21
Create Date: 2026-09-02 16:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "7b2e6c8d4f10"
down_revision: str | Sequence[str] | None = "4f3d5a7b9c21"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """增加绑定匹配报告的学习计划和有序任务。"""
    op.create_table(
        "study_plans",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("match_report_id", sa.Integer(), nullable=False),
        sa.Column("deadline", sa.Date(), nullable=True),
        sa.Column("generation_method", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["match_report_id"],
            ["match_reports.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "match_report_id",
            name="uq_study_plans_match_report_id",
        ),
    )
    with op.batch_alter_table("study_plans", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_study_plans_match_report_id"),
            ["match_report_id"],
            unique=False,
        )

    op.create_table(
        "study_tasks",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("study_plan_id", sa.Integer(), nullable=False),
        sa.Column("skill", sa.String(length=200), nullable=False),
        sa.Column(
            "phase",
            sa.Enum(
                "learn",
                "practice",
                "verify",
                name="studytaskphase",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("completion_criteria", sa.Text(), nullable=False),
        sa.Column("resource_query", sa.String(length=500), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "todo",
                "in_progress",
                "done",
                name="studytaskstatus",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["study_plan_id"],
            ["study_plans.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "study_plan_id",
            "position",
            name="uq_study_tasks_plan_position",
        ),
    )
    with op.batch_alter_table("study_tasks", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_study_tasks_study_plan_id"),
            ["study_plan_id"],
            unique=False,
        )


def downgrade() -> None:
    """删除学习任务和计划表。"""
    with op.batch_alter_table("study_tasks", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_study_tasks_study_plan_id"))
    op.drop_table("study_tasks")

    with op.batch_alter_table("study_plans", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_study_plans_match_report_id"))
    op.drop_table("study_plans")
