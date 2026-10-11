"""Make expired-user events unique.

Revision ID: 20260901_expired_unique
Revises: 20260401_repair
Create Date: 2026-09-01 12:15:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "20260901_expired_unique"
down_revision = "20260401_repair"
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    if "expired_user" not in inspector.get_table_names():
        return

    # Keep the first record for each expiry event.
    connection.execute(
        sa.text("""
            DELETE FROM expired_user
            WHERE id NOT IN (
                SELECT MIN(id)
                FROM expired_user
                GROUP BY original_user_id, expired_at
            )
        """)
    )

    # Old versions did not save the local disabled state. Repair active rows
    # that have a matching expiry history event.
    if "user" in inspector.get_table_names():
        connection.execute(
            sa.text("""
                UPDATE "user"
                SET is_disabled = 1
                WHERE is_disabled = 0
                  AND EXISTS (
                      SELECT 1
                      FROM expired_user
                      WHERE expired_user.original_user_id = "user".id
                        AND expired_user.expired_at = "user".expires
                  )
            """)
        )

    op.create_index(
        "uq_expired_user_event",
        "expired_user",
        ["original_user_id", "expired_at"],
        unique=True,
    )


def downgrade():
    op.drop_index("uq_expired_user_event", table_name="expired_user")
