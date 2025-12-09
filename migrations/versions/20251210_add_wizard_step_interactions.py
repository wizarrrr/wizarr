"""Add interactions JSON column to wizard_step.

This migration adds a flexible JSON column for storing modular interaction
configurations on wizard steps. It replaces the simple require_interaction
boolean with a more extensible structure supporting multiple interaction types.

Supported interaction types:
- click: User must click a link/button in content
- time: User must wait N seconds (countdown timer)
- tos: User must accept Terms of Service
- text_input: User must answer a question correctly
- quiz: User must pass a multi-question quiz

Revision ID: 20251210_add_wizard_interactions
Revises: eecad7c18ac3
Create Date: 2025-12-10
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = "20251210_add_wizard_interactions"
down_revision = "eecad7c18ac3"
branch_labels = None
depends_on = None


def upgrade():
    """Add interactions JSON column to wizard_step.

    Steps:
    1. Add new 'interactions' JSON column (nullable)
    2. Reset all require_interaction to False per migration plan
       (existing steps lose their interaction requirement)
    """
    conn = op.get_bind()
    insp = inspect(conn)

    # Get existing columns
    cols = {c["name"] for c in insp.get_columns("wizard_step")}

    # Add new interactions column if not exists
    if "interactions" not in cols:
        with op.batch_alter_table("wizard_step", schema=None) as batch_op:
            batch_op.add_column(sa.Column("interactions", sa.JSON(), nullable=True))

    # Reset all require_interaction to False (per user decision - no auto-migration)
    # Users will need to reconfigure interactions using the new modular system
    op.execute(sa.text("UPDATE wizard_step SET require_interaction = 0"))


def downgrade():
    """Remove interactions column.

    This downgrade loses all interaction configuration data.
    The legacy require_interaction field remains but will be False.
    """
    with op.batch_alter_table("wizard_step", schema=None) as batch_op:
        batch_op.drop_column("interactions")
