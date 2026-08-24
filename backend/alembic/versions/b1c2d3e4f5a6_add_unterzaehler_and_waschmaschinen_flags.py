"""add strom_unterzaehler_aktiv and wasser_waschmaschinen_aktiv

Revision ID: b1c2d3e4f5a6
Revises: a1b2c3d4e5f6
Create Date: 2026-08-24 10:10:00

Optional-Schalter: Strom-Unterzähler und Wasser-Waschmaschinen-Zähler können
pro Objekt deaktiviert werden (Werte fließen dann nicht in die Berechnung).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "b1c2d3e4f5a6"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("properties", recreate="always") as batch_op:
        batch_op.add_column(
            sa.Column("strom_unterzaehler_aktiv", sa.Boolean(), nullable=False, server_default=sa.true())
        )
        batch_op.add_column(
            sa.Column("wasser_waschmaschinen_aktiv", sa.Boolean(), nullable=False, server_default=sa.true())
        )


def downgrade() -> None:
    with op.batch_alter_table("properties", recreate="always") as batch_op:
        batch_op.drop_column("wasser_waschmaschinen_aktiv")
        batch_op.drop_column("strom_unterzaehler_aktiv")
