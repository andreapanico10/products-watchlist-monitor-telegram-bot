"""add_user_fields_first_name_last_name_language_code_is_bot_is_premium

Revision ID: 488ecb308b64
Revises: 
Create Date: 2025-12-30 22:55:56.304458

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '488ecb308b64'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new columns to users table
    op.add_column('users', sa.Column('first_name', sa.String(), nullable=True))
    op.add_column('users', sa.Column('last_name', sa.String(), nullable=True))
    op.add_column('users', sa.Column('language_code', sa.String(), nullable=True))
    op.add_column('users', sa.Column('is_bot', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('users', sa.Column('is_premium', sa.Boolean(), nullable=True))
    op.add_column('users', sa.Column('updated_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=True))
    
    # Update existing rows: set is_bot to false if NULL (shouldn't happen, but safe)
    op.execute("UPDATE users SET is_bot = false WHERE is_bot IS NULL")


def downgrade() -> None:
    # Remove columns
    op.drop_column('users', 'updated_at')
    op.drop_column('users', 'is_premium')
    op.drop_column('users', 'is_bot')
    op.drop_column('users', 'language_code')
    op.drop_column('users', 'last_name')
    op.drop_column('users', 'first_name')
