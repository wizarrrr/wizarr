"""add external enrollment fields to invitations

Revision ID: bb257e476e63
Revises: 20260401_repair
Create Date: 2026-07-02 19:41:37.090126

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "bb257e476e63"
down_revision = "20260401_repair"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("invitation", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "account_creation_mode",
                sa.String(),
                nullable=False,
                server_default="wizarr",
            ),
        )
        batch_op.add_column(
            sa.Column(
                "external_enrollment_provider",
                sa.String(),
                nullable=False,
                server_default="static_url",
            ),
        )
        batch_op.add_column(
            sa.Column(
                "external_enrollment_url",
                sa.String(),
                nullable=True,
            ),
        )
        batch_op.add_column(
            sa.Column(
                "external_enrollment_append_context",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("1"),
            ),
        )


def downgrade():
    with op.batch_alter_table("invitation", schema=None) as batch_op:
        batch_op.drop_column("external_enrollment_append_context")
        batch_op.drop_column("external_enrollment_url")
        batch_op.drop_column("external_enrollment_provider")
        batch_op.drop_column("account_creation_mode")
