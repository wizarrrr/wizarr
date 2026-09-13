"""Add api_check field to wizard_step

Revision ID: 20260825_apichk
Revises: 20260401_repair
Create Date: 2026-08-25

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260825_apichk"
down_revision = "20260401_repair"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("wizard_step", schema=None) as batch_op:
        batch_op.add_column(sa.Column("api_check", sa.JSON(), nullable=True))


def downgrade():
    with op.batch_alter_table("wizard_step", schema=None) as batch_op:
        batch_op.drop_column("api_check")
