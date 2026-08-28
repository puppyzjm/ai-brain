"""create ai_usage_logs

Revision ID: 0007
Revises: 0006
Create Date: 2025-01-01
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ai_usage_logs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, primary_key=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("conversation_id", sa.BigInteger(), sa.ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True),
        sa.Column("type", sa.String(length=20), nullable=False),
        sa.Column("model", sa.String(length=50), nullable=False),
        sa.Column("prompt_tokens", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("completion_tokens", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("total_tokens", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("latency_ms", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("status", sa.String(length=20), nullable=False, server_default=sa.text("'success'")),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_check_constraint(
        "chk_usage_type", "ai_usage_logs", "type IN ('chat', 'rag', 'summary', 'agent')"
    )
    op.create_check_constraint(
        "chk_usage_status", "ai_usage_logs", "status IN ('success', 'failed')"
    )
    op.create_check_constraint(
        "chk_usage_nonneg", "ai_usage_logs",
        "prompt_tokens >= 0 AND completion_tokens >= 0 "
        "AND total_tokens >= 0 AND latency_ms >= 0",
    )
    op.execute(
        "CREATE INDEX idx_usage_user_created "
        "ON ai_usage_logs (user_id, created_at DESC)"
    )


def downgrade() -> None:
    op.drop_table("ai_usage_logs")
