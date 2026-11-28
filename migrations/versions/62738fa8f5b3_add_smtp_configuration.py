"""add smtp configuration table

Revision ID: 62738fa8f5b3
Revises: 20261013_plex_invite_restrictions
Create Date: 2026-10-27 23:39:02.652763

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "62738fa8f5b3"
down_revision = "20261013_plex_invite_restrictions"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "smtp_configuration",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("host", sa.String(), nullable=False),
        sa.Column("port", sa.Integer(), nullable=False),
        sa.Column("encryption", sa.String(), nullable=False),
        sa.Column("username", sa.String(), nullable=True),
        sa.Column("password_encrypted", sa.String(), nullable=True),
        sa.Column("from_email", sa.String(), nullable=False),
        sa.Column("from_name", sa.String(), nullable=True),
        sa.Column("reminder_days_before", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade():
    op.drop_table("smtp_configuration")
