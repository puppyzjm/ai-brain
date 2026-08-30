"""add avatar to users

Revision ID: 0012
Revises: 0011
Create Date: 2026-08-30
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0012"
down_revision: Union[str, None] = "0011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("avatar", sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "avatar")
