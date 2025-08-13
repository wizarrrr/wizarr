"""Squashed: Overhaul wizard/connections system, add server-specific expiry, and expired users tracking

Revision ID: 20250729_squashed_connections_expiry_system
Revises: 0597748a6fef
Create Date: 2025-07-29 21:15:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = "20250729_squashed_connections_expiry_system"
down_revision = "0597748a6fef"
branch_labels = None
depends_on = None


def upgrade():
    # Get database connection
    connection = op.get_bind()

    # Check if tables already exist (handles interrupted migrations from Watchtower updates)
    inspector = sa.inspect(connection)
    existing_tables = inspector.get_table_names()

    # Create connection table (with connection_type field) only if it doesn't exist
    if "ombi_connection" not in existing_tables:
        op.create_table(
            "ombi_connection",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column(
                "connection_type", sa.String(), nullable=False, server_default="ombi"
            ),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("url", sa.String(), nullable=True),
            sa.Column("api_key", sa.String(), nullable=True),
            sa.Column("media_server_id", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(
                ["media_server_id"], ["media_server.id"], ondelete="CASCADE"
            ),
            sa.PrimaryKeyConstraint("id"),
        )

    # Add expires column to invitation_servers table for per-server expiry (only if it doesn't exist)
    try:
        existing_columns = [
            col["name"] for col in inspector.get_columns("invitation_server")
        ]
        if "expires" not in existing_columns:
            op.add_column(
                "invitation_server", sa.Column("expires", sa.DateTime(), nullable=True)
            )
    except Exception:
        # If invitation_server table doesn't exist, the column add will fail anyway
        pass

    # Create expired_user table to track deleted users (only if it doesn't exist)
    if "expired_user" not in existing_tables:
        op.create_table(
            "expired_user",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("original_user_id", sa.Integer(), nullable=False),
            sa.Column("username", sa.String(), nullable=False),
            sa.Column("email", sa.String(), nullable=True),
            sa.Column("invitation_code", sa.String(), nullable=True),
            sa.Column("server_id", sa.Integer(), nullable=True),
            sa.Column("expired_at", sa.DateTime(), nullable=False),
            sa.Column("deleted_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(
                ["server_id"],
                ["media_server.id"],
            ),
            sa.PrimaryKeyConstraint("id"),
        )

    # Get current settings values
    result = connection.execute(
        text(
            "SELECT key, value FROM settings WHERE key IN ('discord_id', 'overseerr_url', 'ombi_api_key')"
        )
    )
    settings = {row[0]: row[1] for row in result}

    discord_id = (
        settings.get("discord_id", "").strip() if settings.get("discord_id") else None
    )
    overseerr_url = (
        settings.get("overseerr_url", "").strip()
        if settings.get("overseerr_url")
        else None
    )
    ombi_api_key = (
        settings.get("ombi_api_key", "").strip()
        if settings.get("ombi_api_key")
        else None
    )

    # Create connections for existing Plex and Emby servers if ombi_api_key exists
    if ombi_api_key and overseerr_url:
        # Get all Plex and Emby servers
        servers_result = connection.execute(
            text(
                "SELECT id, name FROM media_server WHERE server_type IN ('plex', 'emby')"
            )
        )

        for server_id, server_name in servers_result:
            connection.execute(
                text("""
                INSERT INTO ombi_connection (connection_type, name, url, api_key, media_server_id, created_at, updated_at)
                VALUES ('ombi', :name, :url, :api_key, :server_id, datetime('now'), datetime('now'))
            """),
                {
                    "name": f"Ombi for {server_name}",
                    "url": overseerr_url,
                    "api_key": ombi_api_key,
                    "server_id": server_id,
                },
            )

    # Migrate wizard steps - replace variables or delete steps
    steps_result = connection.execute(text("SELECT id, markdown FROM wizard_step"))

    for step_id, markdown in steps_result:
        if not markdown:
            continue

        updated_markdown = markdown
        should_delete = False

        # Check for Discord template variables
        if "{{ discord_id }}" in updated_markdown:
            if not discord_id:
                should_delete = True
            else:
                updated_markdown = updated_markdown.replace(
                    "{{ discord_id }}", discord_id
                )

        # Check for Overseerr template variables
        if "{{ overseerr_url }}" in updated_markdown:
            if not overseerr_url:
                should_delete = True
            else:
                updated_markdown = updated_markdown.replace(
                    "{{ overseerr_url }}", overseerr_url
                )

        # Delete or update the step
        if should_delete:
            connection.execute(
                text("DELETE FROM wizard_step WHERE id = :step_id"),
                {"step_id": step_id},
            )
        elif updated_markdown != markdown:
            connection.execute(
                text("UPDATE wizard_step SET markdown = :markdown WHERE id = :step_id"),
                {"markdown": updated_markdown, "step_id": step_id},
            )

    # Remove redundant settings
    connection.execute(
        text(
            "DELETE FROM settings WHERE key IN ('discord_id', 'overseerr_url', 'ombi_api_key')"
        )
    )


def downgrade():
    # Restore settings (best effort - won't have original values)
    connection = op.get_bind()

    # Add back the settings with empty values
    connection.execute(
        text("""
        INSERT OR IGNORE INTO settings (key, value, created_at, updated_at)
        VALUES
        ('discord_id', '', datetime('now'), datetime('now')),
        ('overseerr_url', '', datetime('now'), datetime('now')),
        ('ombi_api_key', '', datetime('now'), datetime('now'))
    """)
    )

    # Drop the tables and columns in reverse order
    op.drop_table("expired_user")
    op.drop_column("invitation_server", "expires")
    op.drop_table("ombi_connection")
