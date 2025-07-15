"""add Jellyfin toggles + cleanup stray library_old (SQLite safe)

Revision ID: 20250702_add_jellyfin_options
Revises: 20250620_add_invitation_server
Create Date: 2025-07-02 21:15:00
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20250702_add_jellyfin_options"
down_revision = "20250620_add_invitation_server"
branch_labels = None
depends_on = None


def upgrade():
    """Add Jellyfin download / live-TV flags and clean stray SQLite artefacts."""

    # ── MediaServer: defaults per server ────────────────────────────
    with op.batch_alter_table("media_server", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "allow_downloads_jellyfin",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),  # existing rows → False
            )
        )
        batch_op.add_column(
            sa.Column(
                "allow_tv_jellyfin",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )

    # ── Invitation: per-invite overrides ───────────────────────────
    with op.batch_alter_table("invitation", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("jellyfin_allow_downloads", sa.Boolean(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("jellyfin_allow_live_tv", sa.Boolean(), nullable=True)
        )

    # ── Safety net: drop lingering library_old copy (SQLite only) ──
    conn = op.get_bind()
    if conn.dialect.name == "sqlite":
        # Disable FK checks so the DROP succeeds even if orphan FKs remain
        conn.exec_driver_sql("PRAGMA foreign_keys = OFF")
        conn.exec_driver_sql("DROP TABLE IF EXISTS library_old")
        conn.exec_driver_sql("PRAGMA foreign_keys = ON")


def downgrade():
    # Reverse the column additions; leave library_old alone (was transient)
    with op.batch_alter_table("invitation", schema=None) as batch_op:
        batch_op.drop_column("jellyfin_allow_live_tv")
        batch_op.drop_column("jellyfin_allow_downloads")

    with op.batch_alter_table("media_server", schema=None) as batch_op:
        batch_op.drop_column("allow_tv_jellyfin")
        batch_op.drop_column("allow_downloads_jellyfin")
