"""make admin account password hash nullable for ldap oidc

Revision ID: db34ebf55e26
Revises: 72172a4aa049
Create Date: 2025-12-26 19:36:16.407096

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "db34ebf55e26"
down_revision = "72172a4aa049"
branch_labels = None
depends_on = None


def upgrade():
    # Make password_hash nullable to support LDAP
    with op.batch_alter_table("admin_account", schema=None) as batch_op:
        batch_op.alter_column("password_hash", existing_type=sa.String(), nullable=True)


def downgrade():
    # Revert password_hash to NOT NULL
    with op.batch_alter_table("admin_account", schema=None) as batch_op:
        batch_op.alter_column(
            "password_hash", existing_type=sa.String(), nullable=False
        )
