# app/services/servers.py

from app.extensions import db
from app.models     import Settings
from .plex_workflow     import list_users as _plex_list, delete_user as _plex_del
from .jellyfin_workflow import list_users as _jf_list,   delete_user as _jf_del

def _mode() -> str:
    """
    Reads the 'server_type' setting from the DB.
    Falls back to None if it isn't set.
    """
    return (
        db.session
          .query(Settings.value)
          .filter_by(key="server_type")
          .scalar()
    )

def list_users():
    return _plex_list() if _mode() == "plex" else _jf_list()

def delete_user(db_id: int):
    return _plex_del(db_id) if _mode() == "plex" else _jf_del(db_id)
