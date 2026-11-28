"""birth time may be unknown; store the Moon sign for those profiles

Revision ID: 0011
Revises: 0010
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0011"
down_revision: Union[str, Sequence[str], None] = "0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("birth_profiles", "birth_time", existing_type=sa.Time(), nullable=True)
    op.add_column("birth_profiles", sa.Column("moon_sign", sa.SmallInteger(), nullable=True))
    # Without a birth time the Moon sign must be stored. Every existing row has a time, so this holds already.
    op.create_check_constraint("ck_birth_profiles_time_or_sign", "birth_profiles",
                               "birth_time IS NOT NULL OR (moon_sign IS NOT NULL AND moon_sign BETWEEN 1 AND 12)")


def downgrade() -> None:
    op.drop_constraint("ck_birth_profiles_time_or_sign", "birth_profiles", type_="check")
    op.drop_column("birth_profiles", "moon_sign")
    # Profiles without a time cannot go back to a required column: give them noon.
    op.execute("UPDATE birth_profiles SET birth_time = '12:00:00' WHERE birth_time IS NULL")
    op.alter_column("birth_profiles", "birth_time", existing_type=sa.Time(), nullable=False)
