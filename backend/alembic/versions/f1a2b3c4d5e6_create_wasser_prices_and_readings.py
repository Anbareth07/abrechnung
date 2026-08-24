"""create wasser prices and readings + property mapping columns

Revision ID: f1a2b3c4d5e6
Revises: e7f8a9b0c1d2
Create Date: 2026-08-24 08:40:00

Wasser-Tarife (Trinkwasser/Schmutzwasser/Niederschlagswasser/Grundgebühr mit
Gültigkeitszeitraum und MwSt) sowie Hauptzählerstände je Objekt. Zusätzlich
Zuordnung zu den Abrechnungskostenstellen (Trinkwasser/Schmutzwasser/Niederschlagswasser).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, None] = "e7f8a9b0c1d2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "wasser_prices",
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
        sa.Column("amount", sa.Numeric(14, 5), nullable=False),
        sa.Column("vat_rate", sa.Numeric(5, 2), nullable=False, server_default="19.00"),
    )
    op.create_index("ix_wasser_prices_property_id", "wasser_prices", ["property_id"])

    op.create_table(
        "wasser_readings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "property_id",
            sa.Integer(),
            sa.ForeignKey("properties.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("reading_date", sa.Date(), nullable=False),
        sa.Column("value", sa.Numeric(14, 4), nullable=False),
    )
    op.create_index("ix_wasser_readings_property_id", "wasser_readings", ["property_id"])

    with op.batch_alter_table("properties", recreate="always") as batch_op:
        batch_op.add_column(sa.Column("wasser_trinkwasser_category_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("wasser_schmutzwasser_category_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("wasser_niederschlag_category_id", sa.Integer(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("properties", recreate="always") as batch_op:
        batch_op.drop_column("wasser_niederschlag_category_id")
        batch_op.drop_column("wasser_schmutzwasser_category_id")
        batch_op.drop_column("wasser_trinkwasser_category_id")

    op.drop_index("ix_wasser_readings_property_id", table_name="wasser_readings")
    op.drop_table("wasser_readings")
    op.drop_index("ix_wasser_prices_property_id", table_name="wasser_prices")
    op.drop_table("wasser_prices")
