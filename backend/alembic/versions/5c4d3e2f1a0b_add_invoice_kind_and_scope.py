"""add invoice kind and scope fields

Revision ID: 5c4d3e2f1a0b
Revises: 3a2b1c0d9e8f
Create Date: 2026-08-23 19:15:00

Rechnungen bekommen eine Art (kind: Grundsteuer, Wasser, …), Felder für die
wiederkehrende Grundsteuer (valid_from + Jahresbetrag) sowie einen optionalen
Wohneinheiten-Bezug (Schornsteinfeger u. ä.).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "5c4d3e2f1a0b"
down_revision: Union[str, None] = "3a2b1c0d9e8f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("invoices") as batch_op:
        batch_op.add_column(sa.Column("kind", sa.String(30), nullable=True))
        batch_op.add_column(sa.Column("valid_from", sa.Date(), nullable=True))
        batch_op.add_column(sa.Column("annual_amount", sa.Numeric(14, 2), nullable=True))
        batch_op.add_column(sa.Column("lease_unit_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_invoices_lease_unit_id",
            "lease_units",
            ["lease_unit_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index("ix_invoices_lease_unit_id", ["lease_unit_id"])


def downgrade() -> None:
    with op.batch_alter_table("invoices") as batch_op:
        batch_op.drop_index("ix_invoices_lease_unit_id")
        batch_op.drop_constraint("fk_invoices_lease_unit_id", type_="foreignkey")
        batch_op.drop_column("lease_unit_id")
        batch_op.drop_column("annual_amount")
        batch_op.drop_column("valid_from")
        batch_op.drop_column("kind")
