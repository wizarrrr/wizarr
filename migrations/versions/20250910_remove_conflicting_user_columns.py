"""Remove conflicting allow_downloads and allow_live_tv columns from User model

Revision ID: 20250910_remove_conflicting_user_columns
Revises: 56f3322bd343
Create Date: 2025-09-10 15:05:42.134255

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20250910_remove_conflicting_user_columns"
down_revision = "56f3322bd343"
branch_labels = None
depends_on = None


def upgrade():
    # Drop conflicting columns that were replaced by properties reading from metadata
    # Check if columns exist before dropping them
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col["name"] for col in inspector.get_columns("user")]

    with op.batch_alter_table("user", schema=None) as batch_op:
        if "allow_downloads" in columns:
            batch_op.drop_column("allow_downloads")
        if "allow_live_tv" in columns:
            batch_op.drop_column("allow_live_tv")


def downgrade():
    # Re-add the columns if needed for rollback
    with op.batch_alter_table("user", schema=None) as batch_op:
        batch_op.add_column(sa.Column("allow_downloads", sa.BOOLEAN(), nullable=True))
        batch_op.add_column(sa.Column("allow_live_tv", sa.BOOLEAN(), nullable=True))
