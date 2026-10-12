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
    # The first version of this migration used batch_alter_table. On SQLite,
    # a SQL expression as server_default makes batch mode rebuild the table.
    # With PRAGMA foreign_keys=ON, the DROP TABLE of that rebuild deletes the
    # child rows through ON DELETE CASCADE, or fails on the library rows. A
    # failed run left this temporary table, which blocks the next run.
    op.execute("DROP TABLE IF EXISTS _alembic_tmp_media_server")

    # Skip the column if an admin added it by hand to get past the failure.
    columns = sa.inspect(op.get_bind()).get_columns("media_server")
    if any(c["name"] == "hide_users_from_login" for c in columns):
        return

    # A plain ALTER TABLE ADD COLUMN does not rebuild the table.
    # Jellyfin hides new users by default. True keeps that for existing servers.
    op.add_column(
        "media_server",
        sa.Column(
            "hide_users_from_login",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
    )


def downgrade():
    # SQLite batch mode rebuilds the table to drop a column. Disable FK
    # enforcement so that the DROP TABLE does not delete the child rows.
    conn = op.get_bind()
    conn.execute(sa.text("PRAGMA foreign_keys=OFF"))
    try:
        with op.batch_alter_table("media_server", schema=None) as batch_op:
            batch_op.drop_column("hide_users_from_login")
    finally:
        conn.execute(sa.text("PRAGMA foreign_keys=ON"))
