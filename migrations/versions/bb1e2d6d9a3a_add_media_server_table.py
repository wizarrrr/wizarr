"""add media server table

Revision ID: bb1e2d6d9a3a
Revises: 56b33a2ca88e
Create Date: 2025-07-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'bb1e2d6d9a3a'
down_revision = '56b33a2ca88e'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'media_server',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('server_type', sa.String(), nullable=False),
        sa.Column('server_name', sa.String(), nullable=False),
        sa.Column('server_url', sa.String(), nullable=False),
        sa.Column('api_key', sa.String(), nullable=True),
        sa.Column('libraries', sa.String(), nullable=True),
        sa.Column('allow_downloads_plex', sa.Boolean(), nullable=True),
        sa.Column('allow_tv_plex', sa.Boolean(), nullable=True),
        sa.Column('overseerr_url', sa.String(), nullable=True),
        sa.Column('ombi_api_key', sa.String(), nullable=True),
        sa.Column('discord_id', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    op.drop_table('media_server')
