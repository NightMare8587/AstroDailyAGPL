"""first name, last name, date of birth and gender on the user (the setup page after sign-in)

Revision ID: 0010
Revises: 0009
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0010"
down_revision: Union[str, Sequence[str], None] = "0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("first_name", sa.String(40), nullable=True))
    op.add_column("users", sa.Column("last_name", sa.String(40), nullable=True))
    op.add_column("users", sa.Column("date_of_birth", sa.Date(), nullable=True))
    op.add_column("users", sa.Column("gender", sa.String(10), nullable=True))


def downgrade() -> None:
    for col in ("gender", "date_of_birth", "last_name", "first_name"):
        op.drop_column("users", col)
