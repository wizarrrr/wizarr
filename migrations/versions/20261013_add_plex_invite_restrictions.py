"""Add Plex content restrictions (label and rating filters) to invitations

Revision ID: 20261013_plex_invite_restrictions
Revises: 20261011_ldap_user_sync_filter
Create Date: 2026-10-13 00:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20261013_plex_invite_restrictions"
down_revision = "20261011_ldap_user_sync_filter"
branch_labels = None
depends_on = None

COLUMNS = ("plex_filter_movies", "plex_filter_television", "plex_filter_music")


def _existing_columns() -> set[str]:
    return {c["name"] for c in sa.inspect(op.get_bind()).get_columns("invitation")}


def upgrade():
    # SQLite has no transactional DDL. A failed batch rebuild of this table
    # leaves the temporary table, which blocks the next rebuild.
    op.execute("DROP TABLE IF EXISTS _alembic_tmp_invitation")

    # A plain ALTER TABLE ADD COLUMN does not rebuild the table, so the
    # ON DELETE CASCADE rows in invitation_server, invitation_user and
    # invite_libraries stay. Skip a column that an admin added by hand.
    existing = _existing_columns()
    for name in COLUMNS:
        if name not in existing:
            op.add_column("invitation", sa.Column(name, sa.JSON(), nullable=True))


def downgrade():
    op.execute("DROP TABLE IF EXISTS _alembic_tmp_invitation")
    to_drop = [name for name in COLUMNS if name in _existing_columns()]
    if not to_drop:
        return

    # SQLite batch mode rebuilds the table to drop a column. Disable FK
    # enforcement so that the DROP TABLE does not delete the child rows.
    conn = op.get_bind()
    is_sqlite = conn.dialect.name == "sqlite"
    if is_sqlite:
        conn.execute(sa.text("PRAGMA foreign_keys=OFF"))
    try:
        with op.batch_alter_table("invitation", schema=None) as batch_op:
            for name in to_drop:
                batch_op.drop_column(name)
    finally:
        if is_sqlite:
            conn.execute(sa.text("PRAGMA foreign_keys=ON"))
