"""saved written compatibility summaries, one per ordered pair of profiles and language

Revision ID: 0016
Revises: 0015
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0016"
down_revision: Union[str, Sequence[str], None] = "0015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "match_summaries",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("first_profile_id", sa.Uuid(), sa.ForeignKey("birth_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("second_profile_id", sa.Uuid(), sa.ForeignKey("birth_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("lang", sa.String(2), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("status", sa.String(12), nullable=False),
        sa.Column("model", sa.String(64), nullable=True),
        sa.Column("tokens_in", sa.Integer(), nullable=True),
        sa.Column("tokens_out", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("first_profile_id", "second_profile_id", "lang", name="uq_match_summary_pair_lang"),
    )
    op.create_index("ix_match_summaries_user_id", "match_summaries", ["user_id"])
    op.create_index("ix_match_summaries_first_profile_id", "match_summaries", ["first_profile_id"])
    op.create_index("ix_match_summaries_second_profile_id", "match_summaries", ["second_profile_id"])


def downgrade() -> None:
    op.drop_table("match_summaries")
