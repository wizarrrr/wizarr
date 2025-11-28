"""Add inactivity threshold to media server

Revision ID: 20251107
Revises: 8ef04799f27f
Create Date: 2025-11-07 13:00:36.384659

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251107'
down_revision = '8ef04799f27f'
branch_labels = None
depends_on = None


def upgrade():
    # Add inactivity_threshold_days column to media_server table
    with op.batch_alter_table("media_server", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("inactivity_threshold_days", sa.Integer(), nullable=True)
        )


def downgrade():
    # Remove inactivity_threshold_days column from media_server table
    with op.batch_alter_table("media_server", schema=None) as batch_op:
        batch_op.drop_column("inactivity_threshold_days")