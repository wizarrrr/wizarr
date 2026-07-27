"""Rename the overseerr connection type / settings key to seerr

Overseerr and Jellyseerr were tracked as a single "overseerr" companion type
(labelled "Overseerr/Jellyseerr"). They have unified into "Seerr", so this
converts existing data to the new identifiers:

* connection rows: connection_type 'overseerr' -> 'seerr'
* legacy settings key: 'overseerr_url' -> 'seerr_url'

Info-only Seerr connections carry no secrets, so this is a pure rename with no
behaviour change. The Seerr companion client still registers "overseerr" as an
alias, so a row that slips through resolves either way.

Revision ID: 20260722_rename_overseerr_to_seerr
Revises: 20260401_repair
Create Date: 2026-07-22 00:00:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = "20260722_rename_overseerr_to_seerr"
down_revision = "20260401_repair"
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    tables = sa.inspect(connection).get_table_names()

    if "ombi_connection" in tables:
        connection.execute(
            text(
                "UPDATE ombi_connection SET connection_type = 'seerr' "
                "WHERE connection_type = 'overseerr'"
            )
        )

    if "settings" in tables:
        # Only rename if the destination key is free, so we never collide with a
        # 'seerr_url' row a newer install may already have seeded.
        connection.execute(
            text(
                "UPDATE settings SET key = 'seerr_url' "
                "WHERE key = 'overseerr_url' "
                "AND NOT EXISTS (SELECT 1 FROM settings WHERE key = 'seerr_url')"
            )
        )


def downgrade():
    connection = op.get_bind()
    tables = sa.inspect(connection).get_table_names()

    if "ombi_connection" in tables:
        connection.execute(
            text(
                "UPDATE ombi_connection SET connection_type = 'overseerr' "
                "WHERE connection_type = 'seerr'"
            )
        )

    if "settings" in tables:
        connection.execute(
            text(
                "UPDATE settings SET key = 'overseerr_url' "
                "WHERE key = 'seerr_url' "
                "AND NOT EXISTS (SELECT 1 FROM settings WHERE key = 'overseerr_url')"
            )
        )
