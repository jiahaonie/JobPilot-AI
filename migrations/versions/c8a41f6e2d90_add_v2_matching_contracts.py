"""增加 V2 岗位要求与匹配报告字段。

Revision ID: c8a41f6e2d90
Revises: 7b2e6c8d4f10
Create Date: 2026-09-08 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c8a41f6e2d90"
down_revision: str | Sequence[str] | None = "7b2e6c8d4f10"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """新增字段并把既有岗位分析明确标记为 V1。"""
    with op.batch_alter_table("job_requirements", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "extraction_version",
                sa.String(length=50),
                nullable=False,
                server_default="job-requirements-v1",
            )
        )
        batch_op.add_column(sa.Column("skill_requirements", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("unscored_requirements", sa.JSON(), nullable=True))

    with op.batch_alter_table("match_reports", schema=None) as batch_op:
        batch_op.add_column(sa.Column("requirement_matches", sa.JSON(), nullable=True))


def downgrade() -> None:
    """移除 V2 扩展字段，不触碰原有 V1 数据。"""
    with op.batch_alter_table("match_reports", schema=None) as batch_op:
        batch_op.drop_column("requirement_matches")

    with op.batch_alter_table("job_requirements", schema=None) as batch_op:
        batch_op.drop_column("unscored_requirements")
        batch_op.drop_column("skill_requirements")
        batch_op.drop_column("extraction_version")
