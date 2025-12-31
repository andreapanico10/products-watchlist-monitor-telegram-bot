"""change_telegram_id_to_bigint

Revision ID: 50c4fd3127e0
Revises: 2ce4cf321681
Create Date: 2025-12-31 09:31:15.926189

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '50c4fd3127e0'
down_revision = '2ce4cf321681'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Change telegram_id from INTEGER to BIGINT in users table
    op.alter_column('users', 'telegram_id',
                    existing_type=sa.Integer(),
                    type_=sa.BigInteger(),
                    existing_nullable=False)
    
    # Change referrer_id from INTEGER to BIGINT in users table
    op.alter_column('users', 'referrer_id',
                    existing_type=sa.Integer(),
                    type_=sa.BigInteger(),
                    existing_nullable=True)
    
    # Change user_id from INTEGER to BIGINT in user_products table
    op.alter_column('user_products', 'user_id',
                    existing_type=sa.Integer(),
                    type_=sa.BigInteger(),
                    existing_nullable=False)


def downgrade() -> None:
    # Revert user_id in user_products table back to INTEGER
    op.alter_column('user_products', 'user_id',
                    existing_type=sa.BigInteger(),
                    type_=sa.Integer(),
                    existing_nullable=False)
    
    # Revert referrer_id in users table back to INTEGER
    op.alter_column('users', 'referrer_id',
                    existing_type=sa.BigInteger(),
                    type_=sa.Integer(),
                    existing_nullable=True)
    
    # Revert telegram_id in users table back to INTEGER
    op.alter_column('users', 'telegram_id',
                    existing_type=sa.BigInteger(),
                    type_=sa.Integer(),
                    existing_nullable=False)
