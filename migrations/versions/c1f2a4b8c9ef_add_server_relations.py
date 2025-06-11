"""add server relations

Revision ID: c1f2a4b8c9ef
Revises: bb1e2d6d9a3a
Create Date: 2025-07-02 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = 'c1f2a4b8c9ef'
down_revision = 'bb1e2d6d9a3a'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('invitation', sa.Column('server_id', sa.Integer(), nullable=True))
    op.add_column('user', sa.Column('server_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_invitation_server_id', 'invitation', 'media_server', ['server_id'], ['id'])
    op.create_foreign_key('fk_user_server_id', 'user', 'media_server', ['server_id'], ['id'])


def downgrade():
    op.drop_constraint('fk_user_server_id', 'user', type_='foreignkey')
    op.drop_constraint('fk_invitation_server_id', 'invitation', type_='foreignkey')
    op.drop_column('user', 'server_id')
    op.drop_column('invitation', 'server_id')
