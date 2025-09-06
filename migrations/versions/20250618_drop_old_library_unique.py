"""drop leftover unique constraint on library.external_id (SQLite safe)

Revision ID: 20250618b_drop_old_library_unique
Revises: 20250618_library_unique_per_server
Create Date: 2025-06-18 21:20:00
"""

import sqlalchemy as sa
from alembic import op

revision = "20250618b_drop_old_library_unique"
down_revision = "20250618_library_unique_per_server"
branch_labels = None
depends_on = None


def _drop_unique_idx_on_external_id(conn):
    """For SQLite, unique(column) is implemented as a unique index.  This helper
    finds any *unique* index that covers exactly [external_id] and drops it.
    """

    idx_rows = conn.execute(sa.text("PRAGMA index_list('library')")).fetchall()
    for row in idx_rows:
        # Row layout: (seq, name, unique, origin, partial) – name is column 1, unique flag col 2
        idx_name = row[1]
        is_unique = row[2] == 1
        if not is_unique:
            continue

        cols_info = conn.execute(sa.text(f"PRAGMA index_info('{idx_name}')")).fetchall()
        cols = [ci[2] for ci in cols_info]  # ci: (seqno, cid, name)
        if cols == ["external_id"]:
            conn.exec_driver_sql(f'DROP INDEX "{idx_name}"')


def upgrade():
    conn = op.get_bind()

    if conn.dialect.name == "sqlite":
        _drop_unique_idx_on_external_id(conn)
    else:
        # Non-SQLite engines should already have had the unique constraint dropped
        pass

    # Ensure the composite unique constraint exists (creates no-op if present)
    with op.batch_alter_table("library", schema=None) as batch_op:
        batch_op.create_unique_constraint(
            "uq_library_external_server", ["external_id", "server_id"]
        )


def downgrade():
    # no reverse migration required
    pass
