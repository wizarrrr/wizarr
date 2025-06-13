"""
add external url field to media_server

Revision ID: 20250613_external_url
Revises: 20250612_migrate_settings_to_media_server
Create Date: 2025-06-13 00:00:00

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20250613_external_url'
down_revision = '23bf17eccf13'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('media_server', schema=None) as batch_op:
        batch_op.add_column(sa.Column('external_url', sa.String(), nullable=True))


def downgrade():
    with op.batch_alter_table('media_server', schema=None) as batch_op:
        batch_op.drop_column('external_url') 