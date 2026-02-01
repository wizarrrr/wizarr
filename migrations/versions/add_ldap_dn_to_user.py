"""add is_ldap_user to user table

Revision ID: add_ldap_dn_to_user
Revises: 838b7b1a49ef
Create Date: 2025-12-27 15:30:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "add_ldap_dn_to_user"
down_revision = "838b7b1a49ef"
branch_labels = None
depends_on = None


def upgrade():
    # Add is_ldap_user column to user table
    with op.batch_alter_table("user", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("is_ldap_user", sa.Boolean(), nullable=False, server_default="0")
        )


def downgrade():
    # Remove is_ldap_user column from user table
    with op.batch_alter_table("user", schema=None) as batch_op:
        batch_op.drop_column("is_ldap_user")
