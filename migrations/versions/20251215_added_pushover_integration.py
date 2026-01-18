"""20251215_added_pushover_integration
Revision ID: add_pushover_integration
Revises: eecad7c18ac3
Create Date: 2025-12-15 14:07:53
"""

from alembic import op
import sqlalchemy as sa

revision = 'add_pushover_integration'
down_revision = 'eecad7c18ac3'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('notification', sa.Column('user_key', sa.String(length=50), nullable=True))
    op.add_column('notification', sa.Column('api_token', sa.String(length=50), nullable=True))

def downgrade():
    op.drop_column('notification', 'api_token')
    op.drop_column('notification', 'user_key')
