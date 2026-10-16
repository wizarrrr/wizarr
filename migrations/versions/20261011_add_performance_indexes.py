"""Add indexes for user sync, invitation lookups and activity history

Revision ID: 9c3e5a7d1b20
Revises: f4a2b81c60d7
Create Date: 2026-10-11 12:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "9c3e5a7d1b20"
down_revision = "f4a2b81c60d7"
branch_labels = None
depends_on = None


def upgrade():
    # Historical imports did not set reference_id. Each session without a
    # reference is its own group, so the history grid can group on the column
    # and use an index instead of a CASE expression.
    op.execute(
        "UPDATE activity_session SET reference_id = id WHERE reference_id IS NULL"
    )

    op.create_index("ix_user_server_email", "user", ["server_id", "email"])
    op.create_index("ix_user_server_token", "user", ["server_id", "token"])
    op.create_index(
        "ix_user_server_lower_username",
        "user",
        ["server_id", sa.text("lower(username)")],
    )
    op.create_index("ix_user_identity_id", "user", ["identity_id"])
    op.create_index("ix_invitation_code", "invitation", ["code"])
    op.create_index("ix_invitation_user_user_id", "invitation_user", ["user_id"])

    op.create_index(
        "ix_activity_session_updated_at", "activity_session", ["updated_at"]
    )
    op.create_index(
        "ix_activity_session_reference_started",
        "activity_session",
        ["reference_id", "started_at"],
    )

    # The single-column reference index is a prefix of the new composite index.
    op.drop_index("ix_activity_session_reference_id", table_name="activity_session")
    # Low-cardinality index: the planner picks it for analytics queries and
    # then walks the whole table.
    op.drop_index("ix_activity_session_media_type", table_name="activity_session")
    # The composite (session_id, timestamp) index already covers session_id.
    op.drop_index("ix_activity_snapshot_session_id", table_name="activity_snapshot")
    op.drop_index("ix_activity_snapshot_state", table_name="activity_snapshot")


def downgrade():
    op.create_index("ix_activity_snapshot_state", "activity_snapshot", ["state"])
    op.create_index(
        "ix_activity_snapshot_session_id", "activity_snapshot", ["session_id"]
    )
    op.create_index(
        "ix_activity_session_media_type", "activity_session", ["media_type"]
    )
    op.create_index(
        "ix_activity_session_reference_id", "activity_session", ["reference_id"]
    )

    op.drop_index(
        "ix_activity_session_reference_started", table_name="activity_session"
    )
    op.drop_index("ix_activity_session_updated_at", table_name="activity_session")
    op.drop_index("ix_invitation_user_user_id", table_name="invitation_user")
    op.drop_index("ix_invitation_code", table_name="invitation")
    op.drop_index("ix_user_identity_id", table_name="user")
    op.drop_index("ix_user_server_lower_username", table_name="user")
    op.drop_index("ix_user_server_token", table_name="user")
    op.drop_index("ix_user_server_email", table_name="user")
