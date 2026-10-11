"""20260329_add_user_created_at

Revision ID: 4a39bd26329d
Revises: e6155a91eb50
Create Date: 2026-03-29 16:10:14.582887

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "4a39bd26329d"
down_revision = "e6155a91eb50"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("user", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "created_at",
                sa.DateTime(),
                nullable=True,
                server_default=sa.text("(datetime('now'))"),
            ),
        )


def downgrade():
    with op.batch_alter_table("user", schema=None) as batch_op:
        batch_op.drop_column("created_at")
