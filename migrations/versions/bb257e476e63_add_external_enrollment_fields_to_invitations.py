"""add external enrollment fields to invitations table and create table to track external enrollment state

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

    op.create_table(
        "external_enrollment_state",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(length=128), nullable=False),
        sa.Column("invitation_id", sa.Integer(), nullable=False),
        sa.Column(
            "provider",
            sa.String(),
            nullable=False,
            server_default="static_url",
        ),
        sa.Column("callback_url", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("consumed_at", sa.DateTime(), nullable=True),
        sa.Column("external_subject", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(
            ["invitation_id"],
            ["invitation.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_external_enrollment_state_state",
        "external_enrollment_state",
        ["state"],
        unique=True,
    )
    op.create_index(
        "ix_external_enrollment_state_invitation_id",
        "external_enrollment_state",
        ["invitation_id"],
        unique=False,
    )


def downgrade():
    op.drop_index(
        "ix_external_enrollment_state_invitation_id",
        table_name="external_enrollment_state",
    )
    op.drop_index(
        "ix_external_enrollment_state_state",
        table_name="external_enrollment_state",
    )
    op.drop_table("external_enrollment_state")

    with op.batch_alter_table("invitation", schema=None) as batch_op:
        batch_op.drop_column("external_enrollment_append_context")
        batch_op.drop_column("external_enrollment_url")
        batch_op.drop_column("external_enrollment_provider")
        batch_op.drop_column("account_creation_mode")