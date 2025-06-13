"""migrate legacy Settings to MediaServer rows

Revision ID: 20250612_migrate_settings_to_media_server
Revises: 20250611_add_invitation_server_fk
Create Date: 2025-06-12 10:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column, select, insert, update, text
from sqlalchemy import Integer, String, Boolean
import datetime

# revision identifiers, used by Alembic.
revision = '20250612_migrate_settings_to_media_server'
down_revision = '20250611_add_invitation_server_fk'
branch_labels = None
depends_on = None


SETTINGS_KEYS = [
    "server_type", "server_name", "server_url", "api_key",
    "allow_downloads_plex", "allow_tv_plex"
]

def _get_settings(conn):
    settings_tbl = sa.table(
        'settings',
        sa.column('key', String),
        sa.column('value', String)
    )
    rows = conn.execute(select(settings_tbl.c.key, settings_tbl.c.value)).fetchall()
    return {k: v for k, v in rows}

def upgrade():
    conn = op.get_bind()
    meta = sa.MetaData()
    meta.reflect(bind=conn)

    # Reflect tables
    media_server = meta.tables['media_server']
    library_tbl  = meta.tables['library']
    user_tbl     = meta.tables['user']
    invite_tbl   = meta.tables['invitation']
    settings_tbl = meta.tables['settings']

    # Skip if at least one server already exists
    existing = conn.execute(sa.select(sa.func.count()).select_from(media_server)).scalar()
    if existing:
        return

    s = _get_settings(conn)

    # Compose row values with sensible defaults
    server_type = s.get('server_type', 'plex')
    name        = s.get('server_name', 'Media Server')
    url         = s.get('server_url', '')
    api_key     = s.get('api_key')
    allow_dl    = (s.get('allow_downloads_plex', 'false').lower() == 'true')
    allow_tv    = (s.get('allow_tv_plex', 'false').lower() == 'true')

    # Only create a MediaServer if there is a non-empty URL (i.e., legacy config exists)
    if url:
    # Insert row
        res = conn.execute(
            insert(media_server).values(
                name=name,
                server_type=server_type,
                url=url,
                api_key=api_key,
                allow_downloads_plex=allow_dl,
                allow_tv_plex=allow_tv,
                verified=True,
                created_at=datetime.datetime.utcnow(),
            )
        )
        server_id = res.inserted_primary_key[0]

        # Update related tables where server_id is NULL
        conn.execute(
            update(library_tbl).where(library_tbl.c.server_id.is_(None)).values(server_id=server_id)
        )
        conn.execute(
            update(user_tbl).where(user_tbl.c.server_id.is_(None)).values(server_id=server_id)
        )
        conn.execute(
            update(invite_tbl).where(invite_tbl.c.server_id.is_(None)).values(server_id=server_id)
        )

        # Remove migrated Settings rows
        conn.execute(settings_tbl.delete().where(settings_tbl.c.key.in_(SETTINGS_KEYS)))
        # else: do nothing (no legacy config to migrate)


def downgrade():
    # Downgrade will not restore Settings rows. Only delete created MediaServer row if it was the only row.
    conn = op.get_bind()
    meta = sa.MetaData()
    meta.reflect(bind=conn)
    media_server = meta.tables['media_server']

    # Only attempt if exactly one server present and its verified flag True (heuristic)
    count = conn.execute(sa.select(sa.func.count()).select_from(media_server)).scalar()
    if count == 1:
        conn.execute(media_server.delete())

    # NOTE: server_id columns remain. 