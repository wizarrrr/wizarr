"""Add Emby Connect onboarding option

Revision ID: 20260713_emby_connect
Revises: 20260401_repair
Create Date: 2026-07-13 11:45:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260713_emby_connect"
down_revision = "20260401_repair"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("media_server", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "emby_connect_onboarding",
                sa.Boolean(),
                nullable=False,
                server_default="0",
            )
        )


def downgrade():
    with op.batch_alter_table("media_server", schema=None) as batch_op:
        batch_op.drop_column("emby_connect_onboarding")
