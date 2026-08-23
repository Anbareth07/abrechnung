"""add property strom allocation category

Revision ID: c4d5e6f7a8b9
Revises: b2c3d4e5f6a7
Create Date: 2026-08-23 23:20:00

Strom → Abrechnung: Zuordnung zu einer bestehenden Kostenstelle (statt Umlageschlüssel).
0 = eigene Zeile "Strom", leer = nicht in Abrechnung, >0 = Kostenstellen-ID.
Ersetzt die zuvor ergänzte Spalte strom_allocation_key.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "c4d5e6f7a8b9"
down_revision: Union[str, None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("properties", recreate="always") as batch_op:
        batch_op.drop_column("strom_allocation_key")
        batch_op.add_column(sa.Column("strom_allocation_category_id", sa.Integer(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("properties", recreate="always") as batch_op:
        batch_op.drop_column("strom_allocation_category_id")
        batch_op.add_column(sa.Column("strom_allocation_key", sa.String(20), nullable=True))
