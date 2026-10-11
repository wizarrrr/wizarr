"""Add the Jellyfin option that hides new users from the login screens

Revision ID: 20261011_hide_users_from_login
Revises: 20260903_pushover
Create Date: 2026-10-11 00:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20261011_hide_users_from_login"
down_revision = "20260903_pushover"
branch_labels = None
depends_on = None


def upgrade():
    # Jellyfin hides new users by default. True keeps that for existing servers.
    with op.batch_alter_table("media_server", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "hide_users_from_login",
                sa.Boolean(),
                nullable=False,
                server_default=sa.true(),
            )
        )


def downgrade():
    with op.batch_alter_table("media_server", schema=None) as batch_op:
        batch_op.drop_column("hide_users_from_login")
