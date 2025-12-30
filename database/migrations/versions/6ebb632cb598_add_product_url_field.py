"""add_product_url_field

Revision ID: 6ebb632cb598
Revises: 488ecb308b64
Create Date: 2025-12-30 23:09:47.522016

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6ebb632cb598'
down_revision = '488ecb308b64'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add url column to products table
    op.add_column('products', sa.Column('url', sa.String(), nullable=True))


def downgrade() -> None:
    # Remove url column
    op.drop_column('products', 'url')
