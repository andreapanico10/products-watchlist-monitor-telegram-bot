"""add_referral_system_fields

Revision ID: 2ce4cf321681
Revises: 6ebb632cb598
Create Date: 2025-12-31 09:11:01.885822

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2ce4cf321681'
down_revision = '6ebb632cb598'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add referral system fields to users table
    op.add_column('users', sa.Column('referrer_id', sa.Integer(), nullable=True))
    op.add_column('users', sa.Column('is_vip', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('users', sa.Column('referral_count', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('users', sa.Column('product_limit', sa.Integer(), nullable=False, server_default='3'))
    
    # Add foreign key constraint for referrer_id
    op.create_foreign_key(
        'fk_users_referrer_id',
        'users', 'users',
        ['referrer_id'], ['telegram_id'],
        ondelete='SET NULL'
    )
    
    # Create index on referrer_id for faster queries
    op.create_index('ix_users_referrer_id', 'users', ['referrer_id'])


def downgrade() -> None:
    # Remove index
    op.drop_index('ix_users_referrer_id', 'users')
    
    # Remove foreign key constraint
    op.drop_constraint('fk_users_referrer_id', 'users', type_='foreignkey')
    
    # Remove columns
    op.drop_column('users', 'product_limit')
    op.drop_column('users', 'referral_count')
    op.drop_column('users', 'is_vip')
    op.drop_column('users', 'referrer_id')
