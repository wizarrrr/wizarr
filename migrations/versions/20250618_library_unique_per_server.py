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

    # Attempt to locate the single-column unique constraint on external_id.
    # We check both exact list equality and 1-item set match to be safe.
    old_uq_name = None
    for uq in insp.get_unique_constraints("library"):
        cols = uq.get("column_names") or []
        if len(cols) == 1 and cols[0] == "external_id":
            old_uq_name = uq["name"]
            break

    # Some SQLite DDL auto-generates an index like "sqlite_autoindex_library_1".
    # If we didn't find it via inspector, fall back to that conventional name so
    # batch_op.drop_constraint works for most databases.
    fallback_names = ["uq_library_external_id", "external_id", "sqlite_autoindex_library_1"]

    # Use batch mode so SQLite can handle the changes
    with op.batch_alter_table("library", schema=None) as batch_op:
        if old_uq_name:
            batch_op.drop_constraint(old_uq_name, type_="unique")
        else:
            for nm in fallback_names:
                try:
                    batch_op.drop_constraint(nm, type_="unique")
                    break
                except Exception:
                    # Ignore if this name doesn't exist in the target DB
                    pass
        batch_op.create_unique_constraint(
            "uq_library_external_server", ["external_id", "server_id"]
        )


def downgrade():
    with op.batch_alter_table("library", schema=None) as batch_op:
        batch_op.drop_constraint("uq_library_external_server", type_="unique")
        batch_op.create_unique_constraint("uq_library_external_id", ["external_id"]) 