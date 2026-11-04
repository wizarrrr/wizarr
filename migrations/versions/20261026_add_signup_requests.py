"""Add opt-in public access requests without creating media accounts."""

import sqlalchemy as sa
from alembic import op

revision = "20261026_signup_requests"
down_revision = "20261013_plex_invite_restrictions"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "signup_request",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("email", sa.String(254), nullable=False, unique=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("source_hash", sa.String(64), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("reviewed_at", sa.DateTime()),
        sa.Column("reviewed_by", sa.String(255)),
        sa.Column(
            "invitation_id",
            sa.Integer(),
            sa.ForeignKey("invitation.id", ondelete="SET NULL"),
        ),
        sa.Column("email_sent_at", sa.DateTime()),
    )
    op.create_index("ix_signup_request_source_hash", "signup_request", ["source_hash"])
    op.create_index("ix_signup_request_status", "signup_request", ["status"])


def downgrade():
    op.drop_table("signup_request")
