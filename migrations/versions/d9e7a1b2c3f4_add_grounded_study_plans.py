"""增加有依据学习计划和内置资料元数据。

Revision ID: d9e7a1b2c3f4
Revises: c8a41f6e2d90
Create Date: 2026-09-09 10:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d9e7a1b2c3f4"
down_revision: str | Sequence[str] | None = "c8a41f6e2d90"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """为新计划保存覆盖、具体行动和引用快照。"""
    with op.batch_alter_table("study_plans", schema=None) as batch_op:
        batch_op.add_column(sa.Column("coverage", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("generation_metadata", sa.JSON(), nullable=True))

    with op.batch_alter_table("study_tasks", schema=None) as batch_op:
        batch_op.add_column(sa.Column("learning_content", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("action", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("evidence", sa.JSON(), nullable=True))
        batch_op.alter_column("resource_query", existing_type=sa.String(500), nullable=True)

    with op.batch_alter_table("knowledge_documents", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("is_builtin", sa.Boolean(), nullable=False, server_default=sa.false())
        )
        batch_op.add_column(
            sa.Column("approved", sa.Boolean(), nullable=False, server_default=sa.false())
        )
        batch_op.add_column(sa.Column("source_sha256", sa.String(64), nullable=True))
        batch_op.add_column(sa.Column("content_sha256", sa.String(64), nullable=True))
        batch_op.add_column(sa.Column("embedding_model", sa.String(255), nullable=True))
        batch_op.add_column(sa.Column("chunk_size", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("chunk_overlap", sa.Integer(), nullable=True))


def downgrade() -> None:
    """移除本轮新增字段；执行前必须另行备份新增数据。"""
    with op.batch_alter_table("knowledge_documents", schema=None) as batch_op:
        batch_op.drop_column("chunk_overlap")
        batch_op.drop_column("chunk_size")
        batch_op.drop_column("embedding_model")
        batch_op.drop_column("content_sha256")
        batch_op.drop_column("source_sha256")
        batch_op.drop_column("approved")
        batch_op.drop_column("is_builtin")

    with op.batch_alter_table("study_tasks", schema=None) as batch_op:
        batch_op.alter_column("resource_query", existing_type=sa.String(500), nullable=False)
        batch_op.drop_column("evidence")
        batch_op.drop_column("action")
        batch_op.drop_column("learning_content")

    with op.batch_alter_table("study_plans", schema=None) as batch_op:
        batch_op.drop_column("generation_metadata")
        batch_op.drop_column("coverage")
