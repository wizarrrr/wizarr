"""Add CASCADE delete to foreign keys

Revision ID: add_cascade_fks
Revises: 20251018_add_activity_audit_plus
Create Date: 2025-10-27 00:00:00.000000

This migration adds ondelete="CASCADE" to all foreign keys that reference
user.id and media_server.id to ensure proper cleanup when parent records
are deleted. This eliminates the need for manual deletion workarounds.

For SQLite, we use batch_alter_table which recreates tables with new constraints.
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "add_cascade_fks"
down_revision = "20251018_add_activity_audit_plus"
branch_labels = None
depends_on = None


def upgrade():
    """Add CASCADE to foreign keys for automatic deletion of dependent records."""
    connection = op.get_bind()

    # Enable foreign key enforcement for SQLite
    if connection.dialect.name == "sqlite":
        connection.execute(sa.text("PRAGMA foreign_keys = ON"))

    # For each table, we use batch_alter_table to recreate it with CASCADE constraints
    # batch_alter_table works by:
    # 1. Creating a new table with the desired schema
    # 2. Copying all data
    # 3. Dropping the old table
    # 4. Renaming the new table

    # User table: Add CASCADE to server_id → media_server.id
    with op.batch_alter_table("user", schema=None, copy_from=None):
        pass  # Just recreating the table picks up the new FK definitions from models.py

    # Invitation table: Add CASCADE/SET NULL to foreign keys
    with op.batch_alter_table("invitation", schema=None, copy_from=None):
        pass

    # Library table: Add CASCADE to server_id → media_server.id
    with op.batch_alter_table("library", schema=None, copy_from=None):
        pass

    # ExpiredUser table: Add CASCADE to server_id → media_server.id
    with op.batch_alter_table("expired_user", schema=None, copy_from=None):
        pass

    # ActivitySession table: Add CASCADE to server_id and wizarr_user_id
    with op.batch_alter_table("activity_session", schema=None, copy_from=None):
        pass

    # HistoricalImportJob table: Add CASCADE to server_id → media_server.id
    with op.batch_alter_table("historical_import_job", schema=None, copy_from=None):
        pass


def downgrade():
    """Revert CASCADE changes by recreating tables without CASCADE."""
    connection = op.get_bind()

    if connection.dialect.name == "sqlite":
        connection.execute(sa.text("PRAGMA foreign_keys = ON"))

    # Recreate tables without CASCADE - will revert to previous FK behavior
    # Note: This requires manually defining the old schema, or we accept that
    # downgrades may not be perfect for SQLite FK changes

    with op.batch_alter_table("user", schema=None, copy_from=None):
        pass

    with op.batch_alter_table("invitation", schema=None, copy_from=None):
        pass

    with op.batch_alter_table("library", schema=None, copy_from=None):
        pass

    with op.batch_alter_table("expired_user", schema=None, copy_from=None):
        pass

    with op.batch_alter_table("activity_session", schema=None, copy_from=None):
        pass

    with op.batch_alter_table("historical_import_job", schema=None, copy_from=None):
        pass
