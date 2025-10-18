"""Add Plus features: activity monitoring, audit logging, and historical imports

This migration combines the Plus feature additions:
- Activity monitoring: tracks media playback sessions in real-time
- Audit logging: tracks admin actions and system events
- Historical import: background jobs for importing past playback data
- Identity linking: connects activity sessions to Wizarr users/identities

Revision ID: 20251018_add_activity_audit_plus
Revises: 20251005_add_category_to_wizard_step
Create Date: 2025-09-21 15:22:00.164026

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20251018_add_activity_audit_plus"
down_revision = "20251005_add_category_to_wizard_step"
branch_labels = None
depends_on = None


def upgrade():
    # ─────────────────────────────────────────────────────────────
    # Audit Log Table (Plus Feature)
    # ─────────────────────────────────────────────────────────────
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

    # ─────────────────────────────────────────────────────────────
    # Activity Monitoring Tables (Core Feature)
    # ─────────────────────────────────────────────────────────────
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
        sa.Column("transcoding_info", sa.Text(), nullable=True),
        sa.Column("session_metadata", sa.Text(), nullable=True),
        sa.Column("artwork_url", sa.String(), nullable=True),
        sa.Column("thumbnail_url", sa.String(), nullable=True),
        sa.Column("reference_id", sa.Integer(), nullable=True),
        sa.Column("wizarr_user_id", sa.Integer(), nullable=True),
        sa.Column("wizarr_identity_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["server_id"],
            ["media_server.id"],
        ),
        sa.ForeignKeyConstraint(
            ["wizarr_user_id"],
            ["user.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["wizarr_identity_id"],
            ["identity.id"],
            ondelete="SET NULL",
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
    )
    op.create_index(
        "ix_activity_session_wizarr_user_id",
        "activity_session",
        ["wizarr_user_id"],
        unique=False,
    )
    op.create_index(
        "ix_activity_session_wizarr_identity_id",
        "activity_session",
        ["wizarr_identity_id"],
        unique=False,
    )

    # Composite indexes
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

    # Activity snapshot table
    op.create_table(
        "activity_snapshot",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.Column("position_ms", sa.BigInteger(), nullable=True),
        sa.Column("state", sa.String(), nullable=False),
        sa.Column("transcoding_details", sa.Text(), nullable=True),
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
    op.create_index(
        "ix_activity_snapshot_session_timestamp",
        "activity_snapshot",
        ["session_id", "timestamp"],
        unique=False,
    )

    # ─────────────────────────────────────────────────────────────
    # Historical Import Jobs (Plus Feature)
    # ─────────────────────────────────────────────────────────────
    op.create_table(
        "historical_import_job",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("server_id", sa.Integer(), nullable=False),
        sa.Column("days_back", sa.Integer(), nullable=False),
        sa.Column("max_results", sa.Integer(), nullable=True),
        sa.Column(
            "status", sa.String(length=32), nullable=False, server_default="queued"
        ),
        sa.Column("total_fetched", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_processed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_stored", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["server_id"],
            ["media_server.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_historical_import_job_server_id",
        "historical_import_job",
        ["server_id"],
        unique=False,
    )
    op.create_index(
        "ix_historical_import_job_status",
        "historical_import_job",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_historical_import_job_server_status",
        "historical_import_job",
        ["server_id", "status"],
        unique=False,
    )


def downgrade():
    # Drop historical import job table and indexes
    op.drop_index(
        "ix_historical_import_job_server_status",
        table_name="historical_import_job",
    )
    op.drop_index("ix_historical_import_job_status", table_name="historical_import_job")
    op.drop_index(
        "ix_historical_import_job_server_id",
        table_name="historical_import_job",
    )
    op.drop_table("historical_import_job")

    # Drop activity snapshot table and indexes
    op.drop_index(
        "ix_activity_snapshot_session_timestamp", table_name="activity_snapshot"
    )
    op.drop_index("ix_activity_snapshot_state", table_name="activity_snapshot")
    op.drop_index("ix_activity_snapshot_timestamp", table_name="activity_snapshot")
    op.drop_index("ix_activity_snapshot_session_id", table_name="activity_snapshot")
    op.drop_table("activity_snapshot")

    # Drop activity session table and indexes
    op.drop_index("ix_activity_session_user_started", table_name="activity_session")
    op.drop_index("ix_activity_session_server_started", table_name="activity_session")
    op.drop_index(
        "ix_activity_session_wizarr_identity_id", table_name="activity_session"
    )
    op.drop_index("ix_activity_session_wizarr_user_id", table_name="activity_session")
    op.drop_index("ix_activity_session_reference_id", table_name="activity_session")
    op.drop_index("ix_activity_session_session_id", table_name="activity_session")
    op.drop_index("ix_activity_session_media_type", table_name="activity_session")
    op.drop_index("ix_activity_session_active", table_name="activity_session")
    op.drop_index("ix_activity_session_started_at", table_name="activity_session")
    op.drop_index("ix_activity_session_user_name", table_name="activity_session")
    op.drop_index("ix_activity_session_server_id", table_name="activity_session")
    op.drop_table("activity_session")

    # Drop audit log table
    op.drop_table("audit_log")
