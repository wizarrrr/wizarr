#!/usr/bin/env python3
import sqlite3
import json
import datetime
from pathlib import Path

from app import create_app, db
from app.models import Settings, Invitation, User

# Marker file written by your rename step:
marker = Path("/data/database/legacy_backup.json")
if not marker.exists():
    print("[import_legacy] nothing to do")
    exit(0)

# Load backup path
data        = json.loads(marker.read_text())
backup_path = data["backup"]

# Open the legacy DB read-only
legacy = sqlite3.connect(f"file:{backup_path}?mode=ro", uri=True)
cur    = legacy.cursor()

# Map old keys → new keys
KEY_MAP = {
    "server_name":         "server_name",
    "server_type":         "server_type",
    "server_url":          "server_url",
    #"server_api_key":      "api_key", not imported as it would be open to internet if not configured
    "overseerr_url":       "overseerr_url",
    "ombi_api_key":        "ombi_api_key",
    "discord_id":          "discord_id",
}

app = create_app()
with app.app_context():
    # ─── 1) IMPORT SETTINGS ─────────────────────────────────
    # Load all old settings into a dict so we can prefer override
    old = {k: v for k, v in cur.execute("SELECT key, value FROM settings")}
    for old_key, val in old.items():
        if old_key == "version":
            continue

        new_key = KEY_MAP.get(old_key)
        if not new_key:
            continue

        # if both override and raw URL exist, skip the raw URL
        if old_key == "server_url" and old.get("server_url_override"):
            continue

        # parse booleans or leave strings intact
        v = val
        if new_key == "server_verified":
            v = v.lower() == "true"

        # find-or-create, then assign
        row = db.session.query(Settings).filter_by(key=new_key).first()
        if row:
            row.value = v
        else:
            db.session.add(Settings(key=new_key, value=v))

    db.session.commit()

    # ─── 2) IMPORT INVITATIONS ───────────────────────────────
    for (
        code, used, used_at, created, used_by,
        expires, unlimited, duration,
        specific_libraries, plex_allow_sync
    ) in cur.execute("""
        SELECT code, used, used_at, created, used_by,
               expires, unlimited, duration,
               specific_libraries, plex_allow_sync
          FROM invitations
    """):
        if db.session.query(Invitation).filter_by(code=code).first():
            continue

        inv = Invitation(
            code               = code,
            used               = bool(used),
            used_at            = datetime.datetime.fromisoformat(used_at) if used_at else None,
            created            = datetime.datetime.fromisoformat(created),
            used_by_id            = used_by,
            expires            = datetime.datetime.fromisoformat(expires) if expires else None,
            unlimited          = bool(unlimited),
            duration           = duration or "",
            specific_libraries = specific_libraries or "",
            plex_allow_sync    = bool(plex_allow_sync),
        )
        db.session.add(inv)
    db.session.commit()

    # ─── 3) IMPORT USERS ────────────────────────────────────
    for token, username, email, code, expires in cur.execute(
        "SELECT token, username, email, code, expires FROM users"
    ):
        if db.session.query(User).filter_by(token=token).first():
            continue

        usr = User(
            token    = token,
            username = username,
            email    = email or "empty",
            code     = code  or "empty",
            expires  = datetime.datetime.fromisoformat(expires) if expires else None,
        )
        db.session.add(usr)
    db.session.commit()

# Clean up
marker.unlink()
print("[import_legacy] import complete")
