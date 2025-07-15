"""make library external_id unique per server

Revision ID: 20250618_library_unique_per_server
Revises: 124ededf80dc
Create Date: 2025-06-18 21:00:00
"""

import sqlalchemy as sa
from alembic import op

revision = "20250618_library_unique_per_server"
down_revision = "124ededf80dc"
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

    # 1) Drop old unique(external_id) index in a DB-specific way -----------------

    if conn.dialect.name == "sqlite":
        # SQLite cannot drop the implicit unique index created by the inline
        # UNIQUE constraint, so we must recreate the table without it.

        conn.exec_driver_sql("PRAGMA foreign_keys=OFF")
        # 1) rename old table
        op.execute("ALTER TABLE library RENAME TO library_old")

        # 2) create new table with desired constraints
        op.create_table(
            "library",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("external_id", sa.String, nullable=False),
            sa.Column("name", sa.String, nullable=False),
            sa.Column("enabled", sa.Boolean, nullable=False, default=True),
            sa.Column(
                "server_id", sa.Integer, sa.ForeignKey("media_server.id"), nullable=True
            ),
            sa.UniqueConstraint(
                "external_id", "server_id", name="uq_library_external_server"
            ),
        )

        # 3) copy data
        op.execute(
            "INSERT INTO library (id, external_id, name, enabled, server_id) "
            "SELECT id, external_id, name, enabled, server_id FROM library_old"
        )

        # 4) drop old table
        op.execute("DROP TABLE library_old")

        conn.exec_driver_sql("PRAGMA foreign_keys=ON")

        # done
        return  # skip the generic code below

    # --- Non-SQLite engines ---------------------------------------------------
    for uq in insp.get_unique_constraints("library"):
        cols = uq.get("column_names") or []
        if len(cols) == 1 and cols[0] == "external_id":
            from contextlib import suppress

            with suppress(Exception):
                op.drop_constraint(uq["name"], "library", type_="unique")

    # 2) Ensure composite unique(external_id, server_id) exists ------------------
    with op.batch_alter_table("library", schema=None) as batch_op:
        batch_op.create_unique_constraint(
            "uq_library_external_server", ["external_id", "server_id"]
        )


def downgrade():
    with op.batch_alter_table("library", schema=None) as batch_op:
        batch_op.drop_constraint("uq_library_external_server", type_="unique")
        batch_op.create_unique_constraint("uq_library_external_id", ["external_id"])
