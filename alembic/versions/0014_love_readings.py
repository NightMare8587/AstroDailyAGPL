"""saved written love readings, one per profile and language

Revision ID: 0014
Revises: 0013
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0014"
down_revision: Union[str, Sequence[str], None] = "0013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "love_readings",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("profile_id", sa.Uuid(), sa.ForeignKey("birth_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("lang", sa.String(2), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("status", sa.String(12), nullable=False),
        sa.Column("model", sa.String(64), nullable=True),
        sa.Column("tokens_in", sa.Integer(), nullable=True),
        sa.Column("tokens_out", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("profile_id", "lang", name="uq_love_reading_profile_lang"),
    )
    op.create_index("ix_love_readings_user_id", "love_readings", ["user_id"])
    op.create_index("ix_love_readings_profile_id", "love_readings", ["profile_id"])


def downgrade() -> None:
    op.drop_table("love_readings")
