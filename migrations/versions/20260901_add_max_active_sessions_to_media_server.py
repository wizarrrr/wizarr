"""Add max_active_sessions default to MediaServer model

Revision ID: 20260901_mss_default
Revises: 20260901_expired_unique
Create Date: 2026-09-01 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "20260901_mss_default"
down_revision = "20260901_expired_unique"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("media_server", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("max_active_sessions", sa.Integer(), nullable=True)
        )


def downgrade():
    with op.batch_alter_table("media_server", schema=None) as batch_op:
        batch_op.drop_column("max_active_sessions")
