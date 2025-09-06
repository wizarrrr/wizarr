"""Add allow_downloads and allow_live_tv to user table

Revision ID: 6c39692d6f32
Revises: 14a87d76dff1
Create Date: 2025-09-05 12:20:49.924778

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "6c39692d6f32"
down_revision = "14a87d76dff1"
branch_labels = None
depends_on = None


def upgrade():
    # Add allow_downloads and allow_live_tv columns to user table
    with op.batch_alter_table("user", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("allow_downloads", sa.Boolean(), nullable=True, default=False)
        )
        batch_op.add_column(
            sa.Column("allow_live_tv", sa.Boolean(), nullable=True, default=False)
        )


def downgrade():
    # Remove allow_downloads and allow_live_tv columns from user table
    with op.batch_alter_table("user", schema=None) as batch_op:
        batch_op.drop_column("allow_live_tv")
        batch_op.drop_column("allow_downloads")
