"""widget tokens can be revoked: remember when the person last signed out

Revision ID: 0013
Revises: 0012
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0013"
down_revision: Union[str, Sequence[str], None] = "0012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("widget_tokens_revoked_before", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "widget_tokens_revoked_before")
