"""add tenant contact + monthly costs

Revision ID: 4f9e8d7c6b5a
Revises: 7c1a9d2f4b86
Create Date: 2026-08-23 17:30:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '4f9e8d7c6b5a'
down_revision: Union[str, None] = '7c1a9d2f4b86'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('tenants', sa.Column('phone', sa.String(length=40), nullable=True))
    op.add_column('tenants', sa.Column('email', sa.String(length=120), nullable=True))

    op.create_table(
        'monthly_costs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('amount', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_monthly_costs_tenant_id'), 'monthly_costs', ['tenant_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_monthly_costs_tenant_id'), table_name='monthly_costs')
    op.drop_table('monthly_costs')
    op.drop_column('tenants', 'email')
    op.drop_column('tenants', 'phone')
