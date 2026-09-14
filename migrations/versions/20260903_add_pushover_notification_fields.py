"""Add Pushover notification fields

Revision ID: 20260903_pushover
Revises: 20260901_expired_unique
Create Date: 2026-09-03 00:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260903_pushover"
down_revision = "20260901_expired_unique"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("notification", schema=None) as batch_op:
        batch_op.add_column(sa.Column("pushover_user_key", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("pushover_api_token", sa.String(), nullable=True))


def downgrade():
    with op.batch_alter_table("notification", schema=None) as batch_op:
        batch_op.drop_column("pushover_api_token")
        batch_op.drop_column("pushover_user_key")
