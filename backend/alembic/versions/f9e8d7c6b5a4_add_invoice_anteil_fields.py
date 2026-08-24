"""add invoice anteil fields

Revision ID: f9e8d7c6b5a4
Revises: c1d2e3f4a5b6
Create Date: 2026-08-24 12:20:00

Anrechnungsanteil (Zähler/Nenner) an der Rechnung – Betrag × Faktor wird
angerechnet (z. B. Wohnungsanteil laut Feststellbescheid 13044/13764).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "f9e8d7c6b5a4"
down_revision: Union[str, None] = "c1d2e3f4a5b6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("invoices", recreate="always") as batch_op:
        batch_op.add_column(sa.Column("anteil_zaehler", sa.Numeric(16, 4), nullable=True))
        batch_op.add_column(sa.Column("anteil_nenner", sa.Numeric(16, 4), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("invoices", recreate="always") as batch_op:
        batch_op.drop_column("anteil_nenner")
        batch_op.drop_column("anteil_zaehler")
