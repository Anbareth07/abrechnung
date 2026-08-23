"""add property strom allocation key

Revision ID: b2c3d4e5f6a7
Revises: a7b8c9d1e2f3
Create Date: 2026-08-23 23:10:00

Expliziter Umlageschlüssel für Strom in der Abrechnung (je Objekt),
gesetzt im Strom-Modul. Leer = automatisch (Kostenart "Strom", sonst Wohnfläche).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "a7b8c9d1e2f3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("properties", recreate="always") as batch_op:
        batch_op.add_column(sa.Column("strom_allocation_key", sa.String(20), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("properties", recreate="always") as batch_op:
        batch_op.drop_column("strom_allocation_key")
