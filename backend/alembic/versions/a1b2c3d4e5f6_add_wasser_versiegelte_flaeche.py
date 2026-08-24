"""add wasser_versiegelte_flaeche to properties

Revision ID: a1b2c3d4e5f6
Revises: f1a2b3c4d5e6
Create Date: 2026-08-24 09:10:00

Versiegelte Fläche (m²) am Objekt – Berechnungsgrundlage für
Niederschlagswasser (€/m²).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "f1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("properties", recreate="always") as batch_op:
        batch_op.add_column(sa.Column("wasser_versiegelte_flaeche", sa.Numeric(10, 2), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("properties", recreate="always") as batch_op:
        batch_op.drop_column("wasser_versiegelte_flaeche")
