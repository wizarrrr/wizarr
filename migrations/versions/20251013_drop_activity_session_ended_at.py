"""drop ended_at column from activity_session

Revision ID: 5c6fa54db3b1
Revises: 4e1d547c2f7a
Create Date: 2025-10-13 19:30:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = "5c6fa54db3b1"
down_revision = "4e1d547c2f7a"
branch_labels = None
depends_on = None


def _has_column(connection, table_name, column_name):
    inspector = inspect(connection)
    columns = [col["name"] for col in inspector.get_columns(table_name)]
    return column_name in columns


def _has_index(connection, table_name, index_name):
    inspector = inspect(connection)
    indexes = [idx["name"] for idx in inspector.get_indexes(table_name)]
    return index_name in indexes


def upgrade():
    connection = op.get_bind()
    op.execute("DROP TABLE IF EXISTS _alembic_tmp_activity_session")
    if _has_index(connection, "activity_session", "ix_activity_session_ended_at"):
        op.drop_index("ix_activity_session_ended_at", table_name="activity_session")
    if _has_column(connection, "activity_session", "ended_at"):
        with op.batch_alter_table("activity_session", schema=None) as batch_op:
            batch_op.drop_column("ended_at")

    if not _has_column(connection, "activity_session", "active"):
        with op.batch_alter_table("activity_session", schema=None) as batch_op:
            batch_op.add_column(
                sa.Column(
                    "active", sa.Boolean(), nullable=False, server_default=sa.text("1")
                )
            )

    if not _has_index(connection, "activity_session", "ix_activity_session_active"):
        op.create_index(
            "ix_activity_session_active", "activity_session", ["active"], unique=False
        )


def downgrade():
    connection = op.get_bind()
    if _has_index(connection, "activity_session", "ix_activity_session_active"):
        op.drop_index("ix_activity_session_active", table_name="activity_session")

    with op.batch_alter_table("activity_session", schema=None) as batch_op:
        if _has_column(connection, "activity_session", "active"):
            batch_op.drop_column("active")
        batch_op.add_column(sa.Column("ended_at", sa.DateTime(), nullable=True))
    op.create_index(
        "ix_activity_session_ended_at", "activity_session", ["ended_at"], unique=False
    )
