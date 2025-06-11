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
    # SQLite cannot ALTER tables with constraints directly, so use batch mode
    with op.batch_alter_table('invitation') as batch_op:
        batch_op.add_column(sa.Column('server_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            'fk_invitation_server_id', 'media_server', ['server_id'], ['id']
        )

    with op.batch_alter_table('user') as batch_op:
        batch_op.add_column(sa.Column('server_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            'fk_user_server_id', 'media_server', ['server_id'], ['id']
        )


def downgrade():
    with op.batch_alter_table('user') as batch_op:
        batch_op.drop_constraint('fk_user_server_id', type_='foreignkey')
        batch_op.drop_column('server_id')

    with op.batch_alter_table('invitation') as batch_op:
        batch_op.drop_constraint('fk_invitation_server_id', type_='foreignkey')
        batch_op.drop_column('server_id')
