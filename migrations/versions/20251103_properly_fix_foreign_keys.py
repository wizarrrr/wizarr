"""20251103_properly_fix_foreign_keys

Revision ID: 8ef04799f27f
Revises: add_cascade_fks
Create Date: 2025-11-03 14:44:13.437815

This migration properly fixes foreign key constraints using raw SQL table recreation.
SQLite doesn't support altering foreign keys, so we must recreate tables.

The previous migration (add_cascade_fks) used batch_alter_table but failed to set
the correct CASCADE/SET NULL behaviors. This migration uses explicit SQL to ensure
foreign keys work correctly.

Key fixes:
1. user.server_id → media_server.id: CASCADE delete
2. invitation.used_by_id → user.id: SET NULL on delete
3. activity_session.wizarr_user_id → user.id: CASCADE delete
4. invitation_user.user_id → user.id: CASCADE delete (association table)
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "8ef04799f27f"
down_revision = "add_cascade_fks"
branch_labels = None
depends_on = None


def upgrade():
    """Fix foreign key constraints using raw SQL table recreation."""
    connection = op.get_bind()

    if connection.dialect.name == "sqlite":
        # Disable foreign keys temporarily
        connection.execute(sa.text("PRAGMA foreign_keys = OFF"))

        # ──────────────────────────────────────────────────────────────
        # Fix 1: user table - server_id should CASCADE on delete
        # ──────────────────────────────────────────────────────────────
        connection.execute(
            sa.text("""
            CREATE TABLE user_new (
                id INTEGER NOT NULL PRIMARY KEY,
                token VARCHAR NOT NULL,
                username VARCHAR NOT NULL,
                email VARCHAR,
                code VARCHAR NOT NULL,
                photo VARCHAR,
                expires DATETIME,
                server_id INTEGER,
                identity_id INTEGER,
                notes TEXT,
                library_access_json TEXT,
                raw_policies_json TEXT,
                allow_downloads BOOLEAN,
                allow_live_tv BOOLEAN,
                allow_camera_upload BOOLEAN,
                accessible_libraries TEXT,
                is_admin BOOLEAN,
                is_disabled BOOLEAN DEFAULT 0 NOT NULL,
                FOREIGN KEY(server_id) REFERENCES media_server (id) ON DELETE CASCADE,
                FOREIGN KEY(identity_id) REFERENCES identity (id) ON DELETE SET NULL
            )
        """)
        )

        # Copy data
        connection.execute(
            sa.text("""
            INSERT INTO user_new SELECT * FROM user
        """)
        )

        # Drop old table and rename
        connection.execute(sa.text("DROP TABLE user"))
        connection.execute(sa.text("ALTER TABLE user_new RENAME TO user"))

        # ──────────────────────────────────────────────────────────────
        # Fix 2: invitation table - used_by_id should SET NULL on delete
        # ──────────────────────────────────────────────────────────────
        connection.execute(
            sa.text("""
            CREATE TABLE invitation_new (
                id INTEGER NOT NULL PRIMARY KEY,
                code VARCHAR NOT NULL,
                used BOOLEAN NOT NULL,
                used_at DATETIME,
                created DATETIME NOT NULL,
                used_by_id INTEGER,
                expires DATETIME,
                unlimited BOOLEAN,
                duration VARCHAR,
                specific_libraries VARCHAR,
                plex_allow_sync BOOLEAN,
                plex_home BOOLEAN,
                plex_allow_channels BOOLEAN,
                server_id INTEGER,
                wizard_bundle_id INTEGER,
                allow_downloads BOOLEAN,
                allow_live_tv BOOLEAN,
                allow_mobile_uploads BOOLEAN,
                FOREIGN KEY(used_by_id) REFERENCES user (id) ON DELETE SET NULL,
                FOREIGN KEY(server_id) REFERENCES media_server (id) ON DELETE SET NULL,
                FOREIGN KEY(wizard_bundle_id) REFERENCES wizard_bundle (id) ON DELETE SET NULL
            )
        """)
        )

        connection.execute(
            sa.text("""
            INSERT INTO invitation_new SELECT * FROM invitation
        """)
        )

        connection.execute(sa.text("DROP TABLE invitation"))
        connection.execute(sa.text("ALTER TABLE invitation_new RENAME TO invitation"))

        # ──────────────────────────────────────────────────────────────
        # Fix 3: activity_session table - wizarr_user_id should CASCADE
        # ──────────────────────────────────────────────────────────────
        connection.execute(
            sa.text("""
            CREATE TABLE activity_session_new (
                id INTEGER NOT NULL PRIMARY KEY,
                server_id INTEGER NOT NULL,
                session_id VARCHAR NOT NULL,
                user_name VARCHAR NOT NULL,
                user_id VARCHAR,
                media_title VARCHAR NOT NULL,
                media_type VARCHAR,
                media_id VARCHAR,
                series_name VARCHAR,
                season_number INTEGER,
                episode_number INTEGER,
                started_at DATETIME NOT NULL,
                active BOOLEAN DEFAULT 1 NOT NULL,
                duration_ms BIGINT,
                final_position_ms BIGINT,
                progress_percent FLOAT,
                device_name VARCHAR,
                client_name VARCHAR,
                ip_address VARCHAR,
                platform VARCHAR,
                player_version VARCHAR,
                transcoding_info TEXT,
                session_metadata TEXT,
                artwork_url VARCHAR,
                thumbnail_url VARCHAR,
                reference_id INTEGER,
                wizarr_user_id INTEGER,
                wizarr_identity_id INTEGER,
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL,
                FOREIGN KEY(server_id) REFERENCES media_server (id) ON DELETE CASCADE,
                FOREIGN KEY(wizarr_user_id) REFERENCES user (id) ON DELETE CASCADE,
                FOREIGN KEY(wizarr_identity_id) REFERENCES identity (id) ON DELETE SET NULL
            )
        """)
        )

        connection.execute(
            sa.text("""
            INSERT INTO activity_session_new SELECT * FROM activity_session
        """)
        )

        connection.execute(sa.text("DROP TABLE activity_session"))
        connection.execute(
            sa.text("ALTER TABLE activity_session_new RENAME TO activity_session")
        )

        # Recreate indexes for activity_session
        connection.execute(
            sa.text("""
            CREATE INDEX ix_activity_session_server_id ON activity_session (server_id)
        """)
        )
        connection.execute(
            sa.text("""
            CREATE INDEX ix_activity_session_user_name ON activity_session (user_name)
        """)
        )
        connection.execute(
            sa.text("""
            CREATE INDEX ix_activity_session_started_at ON activity_session (started_at)
        """)
        )
        connection.execute(
            sa.text("""
            CREATE INDEX ix_activity_session_active ON activity_session (active)
        """)
        )
        connection.execute(
            sa.text("""
            CREATE INDEX ix_activity_session_media_type ON activity_session (media_type)
        """)
        )
        connection.execute(
            sa.text("""
            CREATE INDEX ix_activity_session_session_id ON activity_session (session_id)
        """)
        )
        connection.execute(
            sa.text("""
            CREATE INDEX ix_activity_session_reference_id ON activity_session (reference_id)
        """)
        )
        connection.execute(
            sa.text("""
            CREATE INDEX ix_activity_session_wizarr_user_id ON activity_session (wizarr_user_id)
        """)
        )
        connection.execute(
            sa.text("""
            CREATE INDEX ix_activity_session_wizarr_identity_id ON activity_session (wizarr_identity_id)
        """)
        )
        connection.execute(
            sa.text("""
            CREATE INDEX ix_activity_session_server_started ON activity_session (server_id, started_at)
        """)
        )
        connection.execute(
            sa.text("""
            CREATE INDEX ix_activity_session_user_started ON activity_session (user_name, started_at)
        """)
        )

        # ──────────────────────────────────────────────────────────────
        # Fix 4: invitation_user table - CASCADE on both FKs
        # ──────────────────────────────────────────────────────────────
        connection.execute(
            sa.text("""
            CREATE TABLE invitation_user_new (
                invite_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                used_at DATETIME NOT NULL,
                server_id INTEGER,
                PRIMARY KEY (invite_id, user_id),
                FOREIGN KEY(invite_id) REFERENCES invitation (id) ON DELETE CASCADE,
                FOREIGN KEY(user_id) REFERENCES user (id) ON DELETE CASCADE,
                FOREIGN KEY(server_id) REFERENCES media_server (id) ON DELETE SET NULL
            )
        """)
        )

        connection.execute(
            sa.text("""
            INSERT INTO invitation_user_new SELECT * FROM invitation_user
        """)
        )

        connection.execute(sa.text("DROP TABLE invitation_user"))
        connection.execute(
            sa.text("ALTER TABLE invitation_user_new RENAME TO invitation_user")
        )

        # Re-enable foreign keys
        connection.execute(sa.text("PRAGMA foreign_keys = ON"))


def downgrade():
    """Downgrade is not supported for FK constraint changes.

    Reverting these changes would require recreating tables again,
    which is risky for production data. If you need to revert,
    restore from a backup.
    """
