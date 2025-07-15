"""add wizard_step table

Revision ID: 20250619_add_wizard_step_table
Revises: 20250618b_drop_old_library_unique
Create Date: 2025-06-19 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "20250619_add_wizard_step_table"
down_revision = "20250618b_drop_old_library_unique"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "wizard_step",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("server_type", sa.String(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(), nullable=True),
        sa.Column("markdown", sa.Text(), nullable=False),
        sa.Column("requires", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("server_type", "position", name="uq_step_server_pos"),
    )


def downgrade():
    op.drop_table("wizard_step")
