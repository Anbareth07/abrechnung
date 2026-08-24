"""add reading source column

Revision ID: d1e2f3a4b5c6
Revises: f9e8d7c6b5a4
Create Date: 2026-08-24 13:05:00

Herkunft eines Zählerstands: "RECHNUNG" (vom Versorger übermittelt, Standard)
oder "ABLESUNG" (selbst abgelesen) – an Strom-, Wasser- und Wohnungszähler-Ständen.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "d1e2f3a4b5c6"
down_revision: Union[str, None] = "f9e8d7c6b5a4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _add_source(table: str) -> None:
    with op.batch_alter_table(table, recreate="always") as batch_op:
        batch_op.add_column(
            sa.Column("source", sa.String(20), nullable=False, server_default="RECHNUNG")
        )


def _drop_source(table: str) -> None:
    with op.batch_alter_table(table, recreate="always") as batch_op:
        batch_op.drop_column("source")


def upgrade() -> None:
    _add_source("strom_readings")
    _add_source("wasser_readings")
    _add_source("meter_readings")


def downgrade() -> None:
    _drop_source("meter_readings")
    _drop_source("wasser_readings")
    _drop_source("strom_readings")
