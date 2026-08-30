"""extend ai_usage_logs type check to include vision

Revision ID: 0011
Revises: 0010
Create Date: 2026-08-30
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0011"
down_revision: Union[str, None] = "0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("chk_usage_type", "ai_usage_logs", type_="check")
    op.create_check_constraint(
        "chk_usage_type",
        "ai_usage_logs",
        "type IN ('chat', 'rag', 'summary', 'agent', 'vision')",
    )


def downgrade() -> None:
    op.drop_constraint("chk_usage_type", "ai_usage_logs", type_="check")
    op.create_check_constraint(
        "chk_usage_type",
        "ai_usage_logs",
        "type IN ('chat', 'rag', 'summary', 'agent')",
    )
