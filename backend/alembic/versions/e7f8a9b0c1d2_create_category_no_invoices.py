"""create category no invoices

Revision ID: e7f8a9b0c1d2
Revises: d6e7f8a9b0c1
Create Date: 2026-08-23 23:55:00

Kennzeichnung je Objekt+Kostenart+Jahr, dass bewusst keine Rechnung vorliegt
(wird vom Vollständigkeits-Check berücksichtigt).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "e7f8a9b0c1d2"
down_revision: Union[str, None] = "d6e7f8a9b0c1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "category_no_invoices",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "property_id",
            sa.Integer(),
            sa.ForeignKey("properties.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "cost_category_id",
            sa.Integer(),
            sa.ForeignKey("cost_categories.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.UniqueConstraint(
            "property_id", "cost_category_id", "year", name="uq_no_invoice_property_cat_year"
        ),
    )
    op.create_index(
        "ix_category_no_invoices_property_id", "category_no_invoices", ["property_id"]
    )
    op.create_index(
        "ix_category_no_invoices_cost_category_id", "category_no_invoices", ["cost_category_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_category_no_invoices_cost_category_id", table_name="category_no_invoices")
    op.drop_index("ix_category_no_invoices_property_id", table_name="category_no_invoices")
    op.drop_table("category_no_invoices")
