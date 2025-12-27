"""remove default_group_dn from ldap_configuration

Revision ID: 63c02005c2d5
Revises: add_ldap_dn_to_user
Create Date: 2025-12-27 15:53:20.300755

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "63c02005c2d5"
down_revision = "add_ldap_dn_to_user"
branch_labels = None
depends_on = None


def upgrade():
    # Remove default_group_dn column from ldap_configuration table
    with op.batch_alter_table("ldap_configuration", schema=None) as batch_op:
        batch_op.drop_column("default_group_dn")


def downgrade():
    # Re-add default_group_dn column to ldap_configuration table
    with op.batch_alter_table("ldap_configuration", schema=None) as batch_op:
        batch_op.add_column(sa.Column("default_group_dn", sa.String(), nullable=True))
