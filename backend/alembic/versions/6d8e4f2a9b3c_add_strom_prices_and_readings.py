"""add strom prices and readings

Revision ID: 6d8e4f2a9b3c
Revises: 5c4d3e2f1a0b
Create Date: 2026-08-23 22:30:00

Strom-Tarifbestandteile (Grundgebühr/Arbeitspreis/Stromsteuer mit Gültigkeitszeitraum
und MwSt) sowie Zählerstände (Haupt-/Unterzähler) je Objekt.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "6d8e4f2a9b3c"
down_revision: Union[str, None] = "5c4d3e2f1a0b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "strom_prices",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "property_id",
            sa.Integer(),
            sa.ForeignKey("properties.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("kind", sa.String(30), nullable=False),
        sa.Column("valid_from", sa.Date(), nullable=False),
        sa.Column("valid_to", sa.Date(), nullable=False),
        sa.Column("amount", sa.Numeric(14, 4), nullable=False),
        sa.Column("vat_rate", sa.Numeric(5, 2), nullable=False, server_default="19.00"),
    )
    op.create_index("ix_strom_prices_property_id", "strom_prices", ["property_id"])

    op.create_table(
        "strom_readings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "property_id",
            sa.Integer(),
            sa.ForeignKey("properties.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", sa.String(30), nullable=False),
        sa.Column("reading_date", sa.Date(), nullable=False),
        sa.Column("value", sa.Numeric(14, 4), nullable=False),
    )
    op.create_index("ix_strom_readings_property_id", "strom_readings", ["property_id"])


def downgrade() -> None:
    op.drop_index("ix_strom_readings_property_id", table_name="strom_readings")
    op.drop_table("strom_readings")
    op.drop_index("ix_strom_prices_property_id", table_name="strom_prices")
    op.drop_table("strom_prices")
