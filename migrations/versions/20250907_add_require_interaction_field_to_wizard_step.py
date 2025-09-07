"""Add require_interaction field to wizard_step

Revision ID: 8f1a2b3c4d5e
Revises: 6c39692d6f32
Create Date: 2025-09-07

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "8f1a2b3c4d5e"
down_revision = "6c39692d6f32"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("wizard_step", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "require_interaction",
                sa.Boolean(),
                nullable=True,
                server_default=sa.false(),
            )
        )
    # Drop server_default to avoid future inserts locking a default at DB level
    with op.batch_alter_table("wizard_step", schema=None) as batch_op:
        batch_op.alter_column("require_interaction", server_default=None)


def downgrade():
    with op.batch_alter_table("wizard_step", schema=None) as batch_op:
        batch_op.drop_column("require_interaction")
