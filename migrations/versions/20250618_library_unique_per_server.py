"""make library external_id unique per server

Revision ID: 20250618_library_unique_per_server
Revises: 124ededf80dc
Create Date: 2025-06-18 21:00:00
"""
from alembic import op
import sqlalchemy as sa

revision = '20250618_library_unique_per_server'
down_revision = '124ededf80dc'
branch_labels = None
depends_on = None


def upgrade():
    """Replace global unique(external_id) with unique(external_id, server_id).

    For SQLite we have to run this inside batch_alter_table so that Alembic
    recreates the table using the copy-&-move strategy, as SQLite cannot ALTER
    constraints in-place.
    """

    conn = op.get_bind()
    insp = sa.inspect(conn)

    # Detect the current unique constraint name on external_id (varies per DB)
    old_uq_name = None
    for uq in insp.get_unique_constraints('library'):
        if uq.get("column_names") == ["external_id"]:
            old_uq_name = uq["name"]
            break

    # Use batch mode so SQLite can handle the changes
    with op.batch_alter_table("library", schema=None) as batch_op:
        if old_uq_name:
            batch_op.drop_constraint(old_uq_name, type_="unique")
        batch_op.create_unique_constraint(
            "uq_library_external_server", ["external_id", "server_id"]
        )


def downgrade():
    with op.batch_alter_table("library", schema=None) as batch_op:
        batch_op.drop_constraint("uq_library_external_server", type_="unique")
        batch_op.create_unique_constraint("uq_library_external_id", ["external_id"]) 