"""redesign techem records to heizperioden sheet

Revision ID: d6e7f8a9b0c1
Revises: c4d5e6f7a8b9
Create Date: 2026-08-23 23:40:00

Techem-Einträge werden zu Heizkosten-Blättern je Objekt und Heizperiode (von–bis)
mit Gasverbrauch/-kosten, Wartung Heizung und Kaminfeger umgebaut.
Der Heizstromanteil wird automatisch aus dem Unterzähler berechnet.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "d6e7f8a9b0c1"
down_revision: Union[str, None] = "c4d5e6f7a8b9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_META = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")


def upgrade() -> None:
    op.drop_table("techem_records")
    op.create_table(
        "techem_records",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "property_id",
            sa.Integer(),
            sa.ForeignKey("properties.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("von", sa.Date(), nullable=False),
        sa.Column("bis", sa.Date(), nullable=False),
        sa.Column("gas_kwh", sa.Numeric(14, 4), nullable=False, server_default="0"),
        sa.Column("gas_cost", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("maintenance_cost", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("chimney_cost", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("meta", _META, nullable=False, server_default=sa.text("'{}'")),
        sa.UniqueConstraint("property_id", "von", "bis", name="uq_techem_property_period"),
    )
    op.create_index("ix_techem_records_property_id", "techem_records", ["property_id"])


def downgrade() -> None:
    op.drop_index("ix_techem_records_property_id", table_name="techem_records")
    op.drop_table("techem_records")
    op.create_table(
        "techem_records",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "property_id",
            sa.Integer(),
            sa.ForeignKey("properties.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("kind", sa.String(30), nullable=False),
        sa.Column("invoice_date", sa.Date(), nullable=False),
        sa.Column("quantity_kwh", sa.Numeric(14, 4), nullable=True),
        sa.Column("gross_amount", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("meta", _META, nullable=False, server_default=sa.text("'{}'")),
    )
    op.create_index("ix_techem_records_property_id", "techem_records", ["property_id"])
