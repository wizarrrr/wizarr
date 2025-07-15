"""
Add invitation_server association table for multi‐server invites and migrate existing data.

Revision ID: 20250620_add_invitation_server
Revises: 20250619_add_wizard_step_table
Create Date: 2025-06-30
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = "20250620_add_invitation_server"
down_revision = "20250619_add_wizard_step_table"
branch_labels = None
depends_on = None


def upgrade():
    # 1) Create new association table -----------------------------------------
    op.create_table(
        "invitation_server",
        sa.Column("invite_id", sa.Integer(), nullable=False),
        sa.Column("server_id", sa.Integer(), nullable=False),
        sa.Column(
            "used", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        sa.Column("used_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["invite_id"],
            ["invitation.id"],
        ),
        sa.ForeignKeyConstraint(
            ["server_id"],
            ["media_server.id"],
        ),
        sa.PrimaryKeyConstraint("invite_id", "server_id"),
    )

    # 2) Back-fill existing single-server invites -----------------------------
    conn = op.get_bind()
    # Only if the old column still exists
    insp = sa.inspect(conn)
    if "invitation" in insp.get_table_names():
        columns = [col["name"] for col in insp.get_columns("invitation")]
        if "server_id" in columns:
            conn.execute(
                text(
                    """
                INSERT INTO invitation_server (invite_id, server_id, used, used_at)
                SELECT id, server_id, used, used_at FROM invitation WHERE server_id IS NOT NULL
                """
                )
            )


def downgrade():
    op.drop_table("invitation_server")
