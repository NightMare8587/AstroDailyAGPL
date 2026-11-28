"""a count of messages sent to the guide that outlives the chats, so deleting a chat cannot reset the daily limit

Revision ID: 0018
Revises: 0017
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0018"
down_revision: Union[str, Sequence[str], None] = "0017"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "chat_usage",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_chat_usage_user_id", "chat_usage", ["user_id"])
    op.create_index("ix_chat_usage_created_at", "chat_usage", ["created_at"])
    # Keep today's count right for messages that already exist.
    op.execute(
        "INSERT INTO chat_usage (user_id, created_at) "
        "SELECT c.user_id, m.created_at FROM chat_messages m JOIN chat_conversations c ON c.id = m.conversation_id "
        "WHERE m.role = 'user'"
    )


def downgrade() -> None:
    op.drop_index("ix_chat_usage_created_at", table_name="chat_usage")
    op.drop_index("ix_chat_usage_user_id", table_name="chat_usage")
    op.drop_table("chat_usage")
