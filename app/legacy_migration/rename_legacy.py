#!/usr/bin/env python3
import sqlite3, pathlib, datetime, json

# where your “new” DB lives, inside your container
DB      = pathlib.Path("/data/database/database.db")
# append timestamp so you don’t collide
BACKUP  = DB.with_suffix(f".{datetime.datetime.now(datetime.UTC):%Y%m%d-%H%M%S}.old")
# marker file path for the importer to notice
MARKER  = pathlib.Path("/data/database/legacy_backup.json")


def is_old(db_path):
    try:
        con = sqlite3.connect(db_path)
        row = con.execute(
            "SELECT value FROM settings WHERE key='version'"
        ).fetchone()
        return row and row[0] == "4.2.0"
    except sqlite3.Error:
        return False


if DB.exists() and is_old(DB):
    DB.rename(BACKUP)
    print(f"[rename_legacy] rotated legacy DB → {BACKUP}")
    # write the JSON marker
    MARKER.write_text(
        json.dumps({"backup": str(BACKUP)}, indent=2),
        encoding="utf-8"
    )
    print(f"[rename_legacy] wrote marker → {MARKER}")
else:
    print("[rename_legacy] no legacy DB found")
