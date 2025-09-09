"""Add user metadata caching fields

Revision ID: 56f3322bd343
Revises: 8f1a2b3c4d5e
Create Date: 2025-09-09 21:13:06.514906

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "56f3322bd343"
down_revision = "8f1a2b3c4d5e"
branch_labels = None
depends_on = None


def upgrade():
    # Add metadata caching fields to user table (only for displayed data)
    with op.batch_alter_table("user", schema=None) as batch_op:
        batch_op.add_column(sa.Column("library_access_json", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("raw_policies_json", sa.Text(), nullable=True))


def downgrade():
    # Remove metadata caching fields from user table
    with op.batch_alter_table("user", schema=None) as batch_op:
        batch_op.drop_column("raw_policies_json")
        batch_op.drop_column("library_access_json")
