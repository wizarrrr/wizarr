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
    op.add_column(
        "user",
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=True,
            server_default=sa.text("(datetime('now'))"),
        ),
    )


def downgrade():
    op.drop_column("user", "created_at")
