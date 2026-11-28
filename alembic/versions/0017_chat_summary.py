"""a short running summary of older chat messages, so the model keeps the thread within its limit

Revision ID: 0017
Revises: 0016
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0017"
down_revision: Union[str, Sequence[str], None] = "0016"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("chat_conversations", sa.Column("summary", sa.Text(), nullable=True))
    op.add_column("chat_conversations", sa.Column("summarized_through", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("chat_conversations", "summarized_through")
    op.drop_column("chat_conversations", "summary")
