"""index places.name_hi for Hindi prefix search

Revision ID: 0009
Revises: 0008
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0009"
down_revision: Union[str, Sequence[str], None] = "0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index("ix_places_name_hi", "places", ["name_hi"], postgresql_ops={"name_hi": "text_pattern_ops"})


def downgrade() -> None:
    op.drop_index("ix_places_name_hi", table_name="places")
