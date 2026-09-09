"""add Pakasir QRIS payment tables

Revision ID: 20260506_pakasir_qris
Revises: eecad7c18ac3
Create Date: 2026-05-06 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "20260506_pakasir_qris"
down_revision = "eecad7c18ac3"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "pakasir_plan",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("duration_days", sa.Integer(), nullable=False),
        sa.Column("server_ids", sa.Text(), nullable=False),
        sa.Column("library_ids", sa.Text(), nullable=True),
        sa.Column(
            "allow_downloads",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "allow_live_tv",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "allow_mobile_uploads",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("invite_expires_days", sa.Integer(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_table(
        "pakasir_order",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("order_id", sa.String(), nullable=False),
        sa.Column("project", sa.String(), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("payment_method", sa.String(), nullable=False),
        sa.Column("payment_url", sa.Text(), nullable=True),
        sa.Column("buyer_email", sa.String(), nullable=True),
        sa.Column("plan_id", sa.Integer(), nullable=False),
        sa.Column("invitation_id", sa.Integer(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("verified_at", sa.DateTime(), nullable=True),
        sa.Column("raw_webhook_payload", sa.Text(), nullable=True),
        sa.Column("raw_detail_payload", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["invitation_id"], ["invitation.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["plan_id"], ["pakasir_plan.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("order_id"),
    )


def downgrade():
    op.drop_table("pakasir_order")
    op.drop_table("pakasir_plan")
