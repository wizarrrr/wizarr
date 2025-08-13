"""squashed: improve invitation foreign key constraints and add tracking columns

Revision ID: 9275889a2179
Revises: 20250729_squashed_connections_expiry_system
Create Date: 2025-08-10 15:12:02.227613

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "9275889a2179"
down_revision = "20250729_squashed_connections_expiry_system"
branch_labels = None
depends_on = None


def upgrade():
    # 1. Add CASCADE constraints to invite_library table
    # SQLite doesn't support ALTER COLUMN for foreign keys, so we need to recreate the table
    op.create_table(
        "invite_library_new",
        sa.Column("invite_id", sa.Integer(), nullable=False),
        sa.Column("library_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["invite_id"], ["invitation.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["library_id"], ["library.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("invite_id", "library_id"),
    )

    # Copy data from old table to new table
    op.execute("INSERT INTO invite_library_new SELECT * FROM invite_library")

    # Drop old table
    op.drop_table("invite_library")

    # Rename new table to original name
    op.rename_table("invite_library_new", "invite_library")

    # 2. Fix invitation_server foreign key constraints with CASCADE
    # Create new table with CASCADE constraints
    op.create_table(
        "invitation_server_new",
        sa.Column("invite_id", sa.Integer(), nullable=False),
        sa.Column("server_id", sa.Integer(), nullable=False),
        sa.Column("used", sa.Boolean(), nullable=False, default=False),
        sa.Column("used_at", sa.DateTime(), nullable=True),
        sa.Column("expires", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["invite_id"], ["invitation.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["server_id"], ["media_server.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("invite_id", "server_id"),
    )

    # Copy data from old table to new table (original table doesn't have the new columns)
    op.execute(
        "INSERT INTO invitation_server_new (invite_id, server_id, used, used_at, expires) SELECT invite_id, server_id, 0, NULL, NULL FROM invitation_server"
    )

    # Drop old table and rename new table
    op.drop_table("invitation_server")
    op.rename_table("invitation_server_new", "invitation_server")


def downgrade():
    # Reverse all changes

    # 1. Restore invitation_server table without new columns and CASCADE constraints
    op.create_table(
        "invitation_server_old",
        sa.Column("invite_id", sa.Integer(), nullable=False),
        sa.Column("server_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["invite_id"], ["invitation.id"]),
        sa.ForeignKeyConstraint(["server_id"], ["media_server.id"]),
        sa.PrimaryKeyConstraint("invite_id", "server_id"),
    )

    # Copy data from current table to old table (dropping the new columns)
    op.execute(
        "INSERT INTO invitation_server_old (invite_id, server_id) SELECT invite_id, server_id FROM invitation_server"
    )

    # Drop current table and rename old table
    op.drop_table("invitation_server")
    op.rename_table("invitation_server_old", "invitation_server")

    # 2. Restore invite_library table without CASCADE constraints
    op.create_table(
        "invite_library_old",
        sa.Column("invite_id", sa.Integer(), nullable=False),
        sa.Column("library_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["invite_id"], ["invitation.id"]),
        sa.ForeignKeyConstraint(["library_id"], ["library.id"]),
        sa.PrimaryKeyConstraint("invite_id", "library_id"),
    )

    op.execute("INSERT INTO invite_library_old SELECT * FROM invite_library")
    op.drop_table("invite_library")
    op.rename_table("invite_library_old", "invite_library")
