"""create agent_tool_calls

Revision ID: 0008
Revises: 0007
Create Date: 2025-01-01
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "agent_tool_calls",
        sa.Column("id", sa.BigInteger(), autoincrement=True, primary_key=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("conversation_id", sa.BigInteger(), sa.ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True),
        sa.Column("message_id", sa.BigInteger(), sa.ForeignKey("messages.id", ondelete="SET NULL"), nullable=True),
        sa.Column("tool_name", sa.String(length=100), nullable=False),
        sa.Column("arguments", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("result", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default=sa.text("'success'")),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_check_constraint(
        "chk_toolcalls_status", "agent_tool_calls", "status IN ('success', 'failed')"
    )
    op.create_check_constraint(
        "chk_toolcalls_nonneg", "agent_tool_calls", "latency_ms >= 0"
    )
    op.execute(
        "CREATE INDEX idx_toolcalls_user_created "
        "ON agent_tool_calls (user_id, created_at DESC)"
    )
    op.create_index("idx_toolcalls_conversation", "agent_tool_calls", ["conversation_id"])


def downgrade() -> None:
    op.drop_table("agent_tool_calls")
