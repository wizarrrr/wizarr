"""Persist the Navidrome administrator username per media server.

Revision ID: 20261022_navidrome_admin_username
Revises: 20261013_plex_invite_restrictions
Create Date: 2026-10-22 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20261022_navidrome_admin_username"
down_revision = "20261013_plex_invite_restrictions"
branch_labels = None
depends_on = None


def upgrade():
    existing = {
        column["name"]
        for column in sa.inspect(op.get_bind()).get_columns("media_server")
    }
    if "server_username" not in existing:
        op.add_column(
            "media_server", sa.Column("server_username", sa.String(), nullable=True)
        )


def downgrade():
    existing = {
        column["name"]
        for column in sa.inspect(op.get_bind()).get_columns("media_server")
    }
    if "server_username" in existing:
        with op.batch_alter_table("media_server", schema=None) as batch_op:
            batch_op.drop_column("server_username")
