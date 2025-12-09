"""Add max_active_sessions to Invitation model

Revision ID: 080eaac6e013
Revises: 8ef04799f27f
Create Date: 2025-11-21 23:06:28.969903

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "080eaac6e013"
down_revision = "8ef04799f27f"
branch_labels = None
depends_on = None


def upgrade():
    # Only add the max_active_sessions column to invitation table
    with op.batch_alter_table("invitation", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("max_active_sessions", sa.Integer(), nullable=True)
        )


def downgrade():
    # Remove the max_active_sessions column from invitation table
    with op.batch_alter_table("invitation", schema=None) as batch_op:
        batch_op.drop_column("max_active_sessions")
