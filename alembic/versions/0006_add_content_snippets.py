"""add content_snippets

Revision ID: 0006
Revises: 0005
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0006"
down_revision: Union[str, Sequence[str], None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "content_snippets",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("signal_key", sa.String(length=64), nullable=False),
        sa.Column("lang", sa.String(length=2), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("variant", sa.SmallInteger(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=12), nullable=False),
        sa.Column("version", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("signal_key", "lang", "kind", "variant", name="uq_content_snippet"),
    )
    op.create_index("ix_content_lookup", "content_snippets", ["signal_key", "lang", "status"])


def downgrade() -> None:
    op.drop_index("ix_content_lookup", table_name="content_snippets")
    op.drop_table("content_snippets")
