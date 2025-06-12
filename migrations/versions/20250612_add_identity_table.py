"""add identity table and FK

Revision ID: 20250612_add_identity_table
Revises: 20250612_migrate_settings_to_media_server
Create Date: 2025-06-12 11:30:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = '20250612_add_identity_table'
down_revision = '20250612_migrate_settings_to_media_server'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'identity',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('primary_email', sa.String(), nullable=True),
        sa.Column('primary_username', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )
    with op.batch_alter_table('user') as batch:
        batch.add_column(sa.Column('identity_id', sa.Integer(), nullable=True))
        batch.create_foreign_key('fk_user_identity', 'identity', ['identity_id'], ['id'])

    # populate: create identity per unique email
    conn = op.get_bind()
    meta = sa.MetaData()
    meta.reflect(bind=conn)
    user_tbl = meta.tables['user']
    identity_tbl = meta.tables['identity']

    emails = conn.execute(sa.select(user_tbl.c.email).distinct()).scalars().all()
    email_to_id = {}
    for email in emails:
        res = conn.execute(identity_tbl.insert().values(primary_email=email))
        email_to_id[email] = res.inserted_primary_key[0]

    # update users
    for email, iid in email_to_id.items():
        conn.execute(user_tbl.update().where(user_tbl.c.email == email).values(identity_id=iid))


def downgrade():
    with op.batch_alter_table('user') as batch:
        batch.drop_constraint('fk_user_identity', type_='foreignkey')
        batch.drop_column('identity_id')
    op.drop_table('identity') 