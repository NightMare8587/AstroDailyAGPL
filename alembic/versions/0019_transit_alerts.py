"""a switch for planet change alerts (sign changes and retrograde turns) in the notification settings

Revision ID: 0019
Revises: 0018
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0019"
down_revision: Union[str, Sequence[str], None] = "0018"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("notification_prefs", sa.Column("transit_enabled", sa.Boolean(), nullable=False,
                                                   server_default=sa.false()))


def downgrade() -> None:
    op.drop_column("notification_prefs", "transit_enabled")
