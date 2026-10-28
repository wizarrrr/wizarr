"""add user expiry reminder sent at

Revision ID: a1c2d3e4f5a6
Revises: 62738fa8f5b3
Create Date: 2026-10-27 23:45:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "a1c2d3e4f5a6"
down_revision = "62738fa8f5b3"
branch_labels = None
depends_on = None

COLUMN = "expiry_reminder_sent_at"


def _existing_columns() -> set[str]:
    return {c["name"] for c in sa.inspect(op.get_bind()).get_columns("user")}


def upgrade():
    # SQLite has no transactional DDL. A failed batch rebuild of this table
    # leaves the temporary table, which blocks the next rebuild.
    op.execute("DROP TABLE IF EXISTS _alembic_tmp_user")

    if COLUMN not in _existing_columns():
        op.add_column("user", sa.Column(COLUMN, sa.DateTime(), nullable=True))


def downgrade():
    op.execute("DROP TABLE IF EXISTS _alembic_tmp_user")
    if COLUMN not in _existing_columns():
        return

    conn = op.get_bind()
    is_sqlite = conn.dialect.name == "sqlite"
    if is_sqlite:
        conn.execute(sa.text("PRAGMA foreign_keys=OFF"))
    try:
        with op.batch_alter_table("user", schema=None) as batch_op:
            batch_op.drop_column(COLUMN)
    finally:
        if is_sqlite:
            conn.execute(sa.text("PRAGMA foreign_keys=ON"))
