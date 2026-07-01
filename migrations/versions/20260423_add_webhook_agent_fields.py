"""Add webhook agent fields to notification table

Revision ID: 20260423_webhook_agent
Revises: 20260401_repair
Create Date: 2026-04-23

"""

import sqlalchemy as sa
from alembic import op

revision = "20260423_webhook_agent"
down_revision = "20260401_repair"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("notification", schema=None) as batch_op:
        batch_op.add_column(sa.Column("webhook_secret", sa.String(), nullable=True))
        batch_op.add_column(
            sa.Column(
                "include_password",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )


def downgrade():
    with op.batch_alter_table("notification", schema=None) as batch_op:
        batch_op.drop_column("include_password")
        batch_op.drop_column("webhook_secret")
