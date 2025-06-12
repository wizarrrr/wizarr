from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20250611_add_invitation_server_fk'
down_revision = '0271b864fd47'
branch_labels = None
depends_on = None

def upgrade():
    with op.batch_alter_table('invitation', schema=None) as batch_op:
        batch_op.add_column(sa.Column('server_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key('fk_invitation_server_id_media_server', 'media_server', ['server_id'], ['id'])


def downgrade():
    with op.batch_alter_table('invitation', schema=None) as batch_op:
        batch_op.drop_constraint('fk_invitation_server_id_media_server', type_='foreignkey')
        batch_op.drop_column('server_id') 