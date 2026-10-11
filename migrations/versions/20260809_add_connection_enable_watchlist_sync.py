"""Add opt-in flag for enabling watchlist sync on a connection

Revision ID: f4a2b81c60d7
Revises: b7d1c93f4a26
Create Date: 2026-08-09 12:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "f4a2b81c60d7"
down_revision = "b7d1c93f4a26"
branch_labels = None
depends_on = None


def upgrade():
    # Off for existing rows, for the same reason provision_plex_users was: a
    # connection configured before this flag existed must keep behaving exactly
    # as it did.
    with op.batch_alter_table("ombi_connection", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "enable_watchlist_sync",
                sa.Boolean(),
                nullable=False,
                server_default="0",
            )
        )


def downgrade():
    with op.batch_alter_table("ombi_connection", schema=None) as batch_op:
        batch_op.drop_column("enable_watchlist_sync")
