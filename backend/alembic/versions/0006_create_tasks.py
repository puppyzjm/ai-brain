"""create tasks

Revision ID: 0006
Revises: 0005
Create Date: 2025-01-01
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tasks",
        sa.Column("id", sa.BigInteger(), autoincrement=True, primary_key=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default=sa.text("'todo'")),
        sa.Column("priority", sa.String(length=10), nullable=False, server_default=sa.text("'medium'")),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_check_constraint(
        "chk_tasks_status", "tasks", "status IN ('todo', 'in_progress', 'done')"
    )
    op.create_check_constraint(
        "chk_tasks_priority", "tasks", "priority IN ('high', 'medium', 'low')"
    )
    op.create_index("idx_tasks_user_status", "tasks", ["user_id", "status"])


def downgrade() -> None:
    op.drop_table("tasks")
