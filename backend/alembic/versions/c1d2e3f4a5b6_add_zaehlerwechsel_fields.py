"""add zaehlerwechsel fields to readings

Revision ID: c1d2e3f4a5b6
Revises: b1c2d3e4f5a6
Create Date: 2026-08-24 10:30:00

Zählerwechsel-Unterstützung für alle Zählerstände: `vor_zaehlerwechsel`
(der Stand ist der letzte des alten Zählers) und `neuer_zaehler_start`
(Startwert des neuen Zählers, Standard 0).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "c1d2e3f4a5b6"
down_revision: Union[str, None] = "b1c2d3e4f5a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    for table in ("meter_readings", "strom_readings", "wasser_readings"):
        with op.batch_alter_table(table, recreate="always") as batch_op:
            batch_op.add_column(
                sa.Column("vor_zaehlerwechsel", sa.Boolean(), nullable=False, server_default=sa.false())
            )
            batch_op.add_column(
                sa.Column(
                    "neuer_zaehler_start", sa.Numeric(14, 4), nullable=False, server_default="0"
                )
            )


def downgrade() -> None:
    for table in ("wasser_readings", "strom_readings", "meter_readings"):
        with op.batch_alter_table(table, recreate="always") as batch_op:
            batch_op.drop_column("neuer_zaehler_start")
            batch_op.drop_column("vor_zaehlerwechsel")
