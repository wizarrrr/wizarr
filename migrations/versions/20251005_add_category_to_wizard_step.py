"""Add category field to wizard_step table

Revision ID: 20251005_add_category_to_wizard_step
Revises: 08a6c8fb44db
Create Date: 2025-10-05 14:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20251005_add_category_to_wizard_step"
down_revision = "08a6c8fb44db"
branch_labels = None
depends_on = None


def upgrade():
    """Add category column and update unique constraint.

    This migration:
    1. Adds a 'category' column with default 'post_invite'
    2. Drops the old unique constraint on (server_type, position)
    3. Creates a new unique constraint on (server_type, category, position)

    All existing wizard steps will default to 'post_invite' category,
    maintaining backward compatibility.
    """
    # For SQLite, we need to recreate the table to modify constraints
    # This is because SQLite doesn't support dropping constraints directly

    # Step 1: Create new table with updated schema
    op.create_table(
        "wizard_step_new",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("server_type", sa.String(), nullable=False),
        sa.Column(
            "category", sa.String(), nullable=False, server_default="post_invite"
        ),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(), nullable=True),
        sa.Column("markdown", sa.Text(), nullable=False),
        sa.Column("requires", sa.JSON(), nullable=True),
        sa.Column("require_interaction", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "server_type", "category", "position", name="uq_step_server_category_pos"
        ),
    )

    # Step 2: Copy data from old table to new table
    # All existing steps get category='post_invite' by default
    op.execute(
        """
        INSERT INTO wizard_step_new
            (id, server_type, category, position, title, markdown, requires,
             require_interaction, created_at, updated_at)
        SELECT
            id, server_type, 'post_invite', position, title, markdown, requires,
            require_interaction, created_at, updated_at
        FROM wizard_step
        """
    )

    # Step 3: Drop old table
    op.drop_table("wizard_step")

    # Step 4: Rename new table to original name
    op.rename_table("wizard_step_new", "wizard_step")


def downgrade():
    """Remove category column and restore old unique constraint.

    This downgrade:
    1. Removes the category column
    2. Restores the old unique constraint on (server_type, position)

    Note: Steps with category='pre_invite' will be lost during downgrade.
    Only steps with category='post_invite' will be preserved.
    """
    # For SQLite, we need to recreate the table

    # Step 1: Create table with old schema
    op.create_table(
        "wizard_step_old",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("server_type", sa.String(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(), nullable=True),
        sa.Column("markdown", sa.Text(), nullable=False),
        sa.Column("requires", sa.JSON(), nullable=True),
        sa.Column("require_interaction", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("server_type", "position", name="uq_step_server_pos"),
    )

    # Step 2: Copy data from new table to old table
    # Only preserve post_invite steps to avoid constraint violations
    op.execute(
        """
        INSERT INTO wizard_step_old
            (id, server_type, position, title, markdown, requires,
             require_interaction, created_at, updated_at)
        SELECT
            id, server_type, position, title, markdown, requires,
            require_interaction, created_at, updated_at
        FROM wizard_step
        WHERE category = 'post_invite'
        """
    )

    # Step 3: Drop new table
    op.drop_table("wizard_step")

    # Step 4: Rename old table to original name
    op.rename_table("wizard_step_old", "wizard_step")
