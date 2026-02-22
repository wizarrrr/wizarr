"""Add default_group_dn to LDAP configuration

Revision ID: 838b7b1a49ef
Revises: db34ebf55e26
Create Date: 2025-12-27 01:10:33.385785

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "838b7b1a49ef"
down_revision = "db34ebf55e26"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("ldap_configuration", schema=None) as batch_op:
        batch_op.add_column(sa.Column("default_group_dn", sa.String(), nullable=True))


def downgrade():
    with op.batch_alter_table("ldap_configuration", schema=None) as batch_op:
        batch_op.drop_column("default_group_dn")
