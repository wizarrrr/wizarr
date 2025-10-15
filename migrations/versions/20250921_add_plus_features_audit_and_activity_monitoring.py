"""Add Plus features: audit logging and activity monitoring

Revision ID: 20250921_plus_features
Revises: 08a6c8fb44db
Create Date: 2025-09-21 15:22:00.164026

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20250921_plus_features"
down_revision = "08a6c8fb44db"
branch_labels = None
depends_on = None


def upgrade():
    # Create audit_log table
    op.create_table(
        "audit_log",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("resource_type", sa.String(), nullable=False),
        sa.Column("resource_id", sa.String(), nullable=True),
        sa.Column("admin_id", sa.Integer(), nullable=True),
        sa.Column("admin_username", sa.String(), nullable=False),
        sa.Column("ip_address", sa.String(), nullable=True),
        sa.Column("user_agent", sa.String(), nullable=True),
        sa.Column("endpoint", sa.String(), nullable=True),
        sa.Column("method", sa.String(), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("details_json", sa.Text(), nullable=True),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["admin_id"],
            ["admin_account.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create activity_session table
    op.create_table(
        "activity_session",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("server_id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.String(), nullable=False),
        sa.Column("user_name", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=True),
        sa.Column("media_title", sa.String(), nullable=False),
        sa.Column("media_type", sa.String(), nullable=True),
        sa.Column("media_id", sa.String(), nullable=True),
        sa.Column("series_name", sa.String(), nullable=True),
        sa.Column("season_number", sa.Integer(), nullable=True),
        sa.Column("episode_number", sa.Integer(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("duration_ms", sa.BigInteger(), nullable=True),
        sa.Column("final_position_ms", sa.BigInteger(), nullable=True),
        sa.Column("progress_percent", sa.Float(), nullable=True),
        sa.Column("device_name", sa.String(), nullable=True),
        sa.Column("client_name", sa.String(), nullable=True),
        sa.Column("ip_address", sa.String(), nullable=True),
        sa.Column("platform", sa.String(), nullable=True),
        sa.Column("player_version", sa.String(), nullable=True),
        sa.Column("transcoding_info", sa.Text(), nullable=True),  # JSON
        sa.Column("session_metadata", sa.Text(), nullable=True),  # JSON
        sa.Column("artwork_url", sa.String(), nullable=True),
        sa.Column("thumbnail_url", sa.String(), nullable=True),
        sa.Column(
            "reference_id", sa.Integer(), nullable=True
        ),  # Added from third migration
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["server_id"],
            ["media_server.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes for activity_session
    op.create_index(
        "ix_activity_session_server_id", "activity_session", ["server_id"], unique=False
    )
    op.create_index(
        "ix_activity_session_user_name", "activity_session", ["user_name"], unique=False
    )
    op.create_index(
        "ix_activity_session_started_at",
        "activity_session",
        ["started_at"],
        unique=False,
    )
    op.create_index(
        "ix_activity_session_active", "activity_session", ["active"], unique=False
    )
    op.create_index(
        "ix_activity_session_media_type",
        "activity_session",
        ["media_type"],
        unique=False,
    )
    op.create_index(
        "ix_activity_session_session_id",
        "activity_session",
        ["session_id"],
        unique=False,
    )
    op.create_index(
        "ix_activity_session_reference_id",
        "activity_session",
        ["reference_id"],
        unique=False,
    )  # From third migration

    # Create composite indexes for common queries
    op.create_index(
        "ix_activity_session_server_started",
        "activity_session",
        ["server_id", "started_at"],
        unique=False,
    )
    op.create_index(
        "ix_activity_session_user_started",
        "activity_session",
        ["user_name", "started_at"],
        unique=False,
    )

    # Create activity_snapshot table
    op.create_table(
        "activity_snapshot",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.Column("position_ms", sa.BigInteger(), nullable=True),
        sa.Column("state", sa.String(), nullable=False),  # playing, paused, stopped
        sa.Column("transcoding_details", sa.Text(), nullable=True),  # JSON
        sa.Column("bandwidth_kbps", sa.Integer(), nullable=True),
        sa.Column("quality", sa.String(), nullable=True),
        sa.Column("subtitle_stream", sa.String(), nullable=True),
        sa.Column("audio_stream", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["session_id"], ["activity_session.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes for activity_snapshot
    op.create_index(
        "ix_activity_snapshot_session_id",
        "activity_snapshot",
        ["session_id"],
        unique=False,
    )
    op.create_index(
        "ix_activity_snapshot_timestamp",
        "activity_snapshot",
        ["timestamp"],
        unique=False,
    )
    op.create_index(
        "ix_activity_snapshot_state", "activity_snapshot", ["state"], unique=False
    )

    # Create composite index for time-series queries
    op.create_index(
        "ix_activity_snapshot_session_timestamp",
        "activity_snapshot",
        ["session_id", "timestamp"],
        unique=False,
    )


def downgrade():
    # Drop indexes first
    op.drop_index(
        "ix_activity_snapshot_session_timestamp", table_name="activity_snapshot"
    )
    op.drop_index("ix_activity_snapshot_state", table_name="activity_snapshot")
    op.drop_index("ix_activity_snapshot_timestamp", table_name="activity_snapshot")
    op.drop_index("ix_activity_snapshot_session_id", table_name="activity_snapshot")

    op.drop_index("ix_activity_session_user_started", table_name="activity_session")
    op.drop_index("ix_activity_session_server_started", table_name="activity_session")
    op.drop_index(
        "ix_activity_session_reference_id", table_name="activity_session"
    )  # From third migration
    op.drop_index("ix_activity_session_session_id", table_name="activity_session")
    op.drop_index("ix_activity_session_media_type", table_name="activity_session")
    op.drop_index("ix_activity_session_active", table_name="activity_session")
    op.drop_index("ix_activity_session_started_at", table_name="activity_session")
    op.drop_index("ix_activity_session_user_name", table_name="activity_session")
    op.drop_index("ix_activity_session_server_id", table_name="activity_session")

    # Drop tables
    op.drop_table("activity_snapshot")
    op.drop_table("activity_session")
    op.drop_table("audit_log")
