"""Add an optional LDAP filter that limits the users that sync imports

Revision ID: 20261011_ldap_user_sync_filter
Revises: 20261011_hide_users_from_login
Create Date: 2026-10-11 00:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20261011_ldap_user_sync_filter"
down_revision = "20261011_hide_users_from_login"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("ldap_configuration", schema=None) as batch_op:
        batch_op.add_column(sa.Column("user_sync_filter", sa.String(), nullable=True))


def downgrade():
    with op.batch_alter_table("ldap_configuration", schema=None) as batch_op:
        batch_op.drop_column("user_sync_filter")
