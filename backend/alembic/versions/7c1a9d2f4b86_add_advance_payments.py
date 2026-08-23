"""add advance_payments

Revision ID: 7c1a9d2f4b86
Revises: e1b389192dff
Create Date: 2026-08-23 16:40:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '7c1a9d2f4b86'
down_revision: Union[str, None] = 'e1b389192dff'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'advance_payments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('valid_from', sa.Date(), nullable=False),
        sa.Column('amount', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_advance_payments_tenant_id'), 'advance_payments', ['tenant_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_advance_payments_tenant_id'), table_name='advance_payments')
    op.drop_table('advance_payments')
