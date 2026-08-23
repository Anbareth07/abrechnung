"""strom price amount 5 decimals

Revision ID: a7b8c9d1e2f3
Revises: 6d8e4f2a9b3c
Create Date: 2026-08-23 22:50:00

Strom-Tarifbeträge (insb. Arbeitspreis €/kWh) mit 5 Nachkommastellen.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "a7b8c9d1e2f3"
down_revision: Union[str, None] = "6d8e4f2a9b3c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("strom_prices", recreate="always") as batch_op:
        batch_op.alter_column("amount", existing_type=sa.Numeric(14, 4), type_=sa.Numeric(14, 5))


def downgrade() -> None:
    with op.batch_alter_table("strom_prices", recreate="always") as batch_op:
        batch_op.alter_column("amount", existing_type=sa.Numeric(14, 5), type_=sa.Numeric(14, 4))
