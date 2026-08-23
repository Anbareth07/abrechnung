"""add is_test flag to properties

Revision ID: 3a2b1c0d9e8f
Revises: 9b8a7c6d5e4f
Create Date: 2026-08-23 18:45:00

Objekte können als Testdaten markiert werden (is_test), um sie über die UI
auszublenden. Das vorhandene „Testobjekt" wird entsprechend markiert.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "3a2b1c0d9e8f"
down_revision: Union[str, None] = "9b8a7c6d5e4f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "properties",
        sa.Column("is_test", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    bind = op.get_bind()
    bind.execute(sa.text("UPDATE properties SET is_test = 1 WHERE name = 'Testobjekt'"))


def downgrade() -> None:
    op.drop_column("properties", "is_test")
