"""Preserve invitation/join provenance independently of hard deletion.

Revision ID: 20261103_invitation_access
Revises: 20261013_plex_invite_restrictions
"""

import sqlalchemy as sa
from alembic import op

revision = "20261103_invitation_access"
down_revision = "20261013_plex_invite_restrictions"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "invitation_access",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("code", sa.String(), nullable=False, unique=True),
        sa.Column("invitation_id", sa.Integer(), nullable=False),
        sa.Column("barrier", sa.Boolean(), nullable=False),
        sa.Column("deleted", sa.Boolean(), nullable=False),
        sa.Column("baseline_complete", sa.Boolean(), nullable=False),
    )
    op.create_table(
        "invitation_join_attempt",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column(
            "access_id",
            sa.String(32),
            sa.ForeignKey("invitation_access.id"),
            nullable=False,
        ),
        sa.Column("server_id", sa.Integer(), nullable=False),
        sa.Column(
            "server_ref_id",
            sa.Integer(),
            sa.ForeignKey("media_server.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("server_url", sa.String(), nullable=False),
        sa.Column("remote_user_id", sa.String(), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("create_started", sa.Boolean(), nullable=False),
        sa.Column("finished", sa.Boolean(), nullable=False),
        sa.Column("remote_state", sa.String(), nullable=False),
    )
    op.create_index(
        "ix_invitation_join_attempt_access_id", "invitation_join_attempt", ["access_id"]
    )
    # Existing invitations predate registered attempts. Even apparently unused
    # rows cannot prove that no old worker created an untracked remote account.
    op.execute("""
        INSERT OR IGNORE INTO invitation_access
            (id, code, invitation_id, barrier, deleted, baseline_complete)
            SELECT lower(hex(randomblob(16))), upper(code), id, 0, 0, 0
            FROM invitation
    """)
    # SQLite is Wizarr's supported database. A trigger covers ORM and bulk deletes
    # without turning invitation deletion into remote account deletion.
    op.execute("""
        CREATE TRIGGER invitation_access_delete BEFORE DELETE ON invitation
        BEGIN
            INSERT OR IGNORE INTO invitation_access
                (id, code, invitation_id, barrier, deleted, baseline_complete)
                VALUES (lower(hex(randomblob(16))), upper(OLD.code), OLD.id, 0, 1, 0);
            UPDATE invitation_access SET deleted = 1,
                baseline_complete = CASE WHEN OLD.create_ldap_user = 1 OR EXISTS (
                    SELECT 1 FROM invitation_server link
                    JOIN media_server server ON server.id = link.server_id
                    WHERE link.invite_id = OLD.id AND server.server_type != 'emby'
                ) OR EXISTS (
                    SELECT 1 FROM media_server server
                    WHERE server.id = OLD.server_id AND server.server_type != 'emby'
                ) THEN 0 ELSE baseline_complete END
                WHERE code = upper(OLD.code);
        END
    """)
    # Remember unsupported provenance even if configuration is later reverted.
    op.execute("""
        CREATE TRIGGER invitation_access_config AFTER UPDATE OF create_ldap_user, server_id ON invitation
        WHEN NEW.create_ldap_user = 1 OR EXISTS (
            SELECT 1 FROM media_server WHERE id = NEW.server_id AND server_type != 'emby'
        ) BEGIN
            UPDATE invitation_access SET baseline_complete = 0
                WHERE code = upper(NEW.code);
        END
    """)
    op.execute("""
        CREATE TRIGGER invitation_access_link AFTER INSERT ON invitation_server
        WHEN EXISTS (SELECT 1 FROM media_server WHERE id = NEW.server_id AND server_type != 'emby')
        BEGIN
            UPDATE invitation_access SET baseline_complete = 0
                WHERE invitation_id = NEW.invite_id AND deleted = 0;
        END
    """)
    op.execute("""
        CREATE TRIGGER invitation_access_server AFTER UPDATE OF server_type ON media_server
        WHEN NEW.server_type != 'emby'
        BEGIN
            UPDATE invitation_access SET baseline_complete = 0 WHERE id IN (
                SELECT access_id FROM invitation_join_attempt WHERE server_ref_id = NEW.id
            ) OR invitation_id IN (
                SELECT id FROM invitation WHERE server_id = NEW.id
                UNION SELECT invite_id FROM invitation_server WHERE server_id = NEW.id
            );
        END
    """)


def downgrade():
    op.execute("DROP TRIGGER invitation_access_server")
    op.execute("DROP TRIGGER invitation_access_link")
    op.execute("DROP TRIGGER invitation_access_config")
    op.execute("DROP TRIGGER invitation_access_delete")
    op.drop_index(
        "ix_invitation_join_attempt_access_id", table_name="invitation_join_attempt"
    )
    op.drop_table("invitation_join_attempt")
    op.drop_table("invitation_access")
