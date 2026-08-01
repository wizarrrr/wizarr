"""Add opt-in flag for provisioning Plex users on a connection

Revision ID: b7d1c93f4a26
Revises: 20260401_repair
Create Date: 2026-07-22 17:05:11.402913

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "b7d1c93f4a26"
down_revision = "20260401_repair"
branch_labels = None
depends_on = None


def upgrade():
    # Off for existing rows: a connection configured before this flag existed
    # must keep behaving exactly as it did.
    with op.batch_alter_table("ombi_connection", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "provision_plex_users",
                sa.Boolean(),
                nullable=False,
                server_default="0",
            )
        )


def downgrade():
    with op.batch_alter_table("ombi_connection", schema=None) as batch_op:
        batch_op.drop_column("provision_plex_users")
