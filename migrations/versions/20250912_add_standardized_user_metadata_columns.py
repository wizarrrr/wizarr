"""Add standardized user metadata columns

Revision ID: 20250912_add_standardized_user_metadata_columns
Revises: 20250910_remove_conflicting_user_columns
Create Date: 2025-09-12 13:39:05.581453

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20250912_add_standardized_user_metadata_columns"
down_revision = "20250910_remove_conflicting_user_columns"
branch_labels = None
depends_on = None


def upgrade():
    # Add standardized user metadata columns (is_admin already exists)
    with op.batch_alter_table("user", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("allow_downloads", sa.Boolean(), nullable=True, default=False)
        )
        batch_op.add_column(
            sa.Column("allow_live_tv", sa.Boolean(), nullable=True, default=False)
        )
        batch_op.add_column(
            sa.Column("allow_camera_upload", sa.Boolean(), nullable=True, default=False)
        )
        batch_op.add_column(
            sa.Column("accessible_libraries", sa.Text(), nullable=True)
        )  # JSON array of library names


def downgrade():
    # Remove standardized user metadata columns (keep is_admin as it existed before)
    with op.batch_alter_table("user", schema=None) as batch_op:
        batch_op.drop_column("accessible_libraries")
        batch_op.drop_column("allow_camera_upload")
        batch_op.drop_column("allow_live_tv")
        batch_op.drop_column("allow_downloads")
