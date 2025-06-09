#!/usr/bin/env sh
set -eu

echo "[entrypoint] 🚀 Starting Wizarr container..."

# ─────────────────────────────────────────────────────────────────────────────
# 1) Handle PUID/PGID setup (only if running as root)
# ─────────────────────────────────────────────────────────────────────────────
# Default values
PUID=${PUID:-1000}
PGID=${PGID:-1000}

if [ "$(id -u)" = "0" ]; then
    echo "[entrypoint] 👤 Setting up user environment with PUID=$PUID and PGID=$PGID"
    
    # Create group and user
    addgroup -S -g "$PGID" wizarrgroup
    adduser -S -G wizarrgroup -u "$PUID" wizarruser
    
    # Fix ownership of important directories
    echo "[entrypoint] 🔧 Fixing ownership of directories..."
    chown -R wizarruser:wizarrgroup /data
    chown -R wizarruser:wizarrgroup /.cache
    chown -R wizarruser:wizarrgroup /opt/default_wizard_steps
    
    # Switch to wizarruser and re-execute this script
    echo "[entrypoint] 🔄 Switching to wizarruser..."
    exec su-exec wizarruser "$0" "$@"
fi

echo "[entrypoint] 👤 Running as user $(id -u):$(id -g)"

# ─────────────────────────────────────────────────────────────────────────────
# 2) Seed wizard steps if the target is truly empty (no visible files at all)
# ─────────────────────────────────────────────────────────────────────────────
TARGET=/data/wizard_steps
DEFAULT=/opt/default_wizard_steps

# ensure the directory exists
mkdir -p "$TARGET"

# only proceed if DEFAULT has content and TARGET really has zero entries
if [ -d "$DEFAULT" ] && [ -z "$(find "$TARGET" -mindepth 1 -print -quit)" ]; then
  echo "[entrypoint] ✨ Seeding default wizard steps into $TARGET…"
  cp -a "$DEFAULT/." "$TARGET/"
else
  echo "[entrypoint] skipping wizard-steps seed (already populated)"
fi

# ─────────────────────────────────────────────────────────────────────────────
# 3) Legacy DB rename + migrations + import
# ─────────────────────────────────────────────────────────────────────────────
echo "[entrypoint] 🔄 Renaming legacy database (if any)…"
uv run python -m app.legacy_migration.rename_legacy

echo "[entrypoint] 🔧 Applying alembic migrations…"
uv run flask db upgrade

echo "[entrypoint] 🗄️ Importing legacy data…"
uv run python -m app.legacy_migration.import_legacy

# ─────────────────────────────────────────────────────────────────────────────
# 4) Hand off to your CMD (e.g. gunicorn)
# ─────────────────────────────────────────────────────────────────────────────
exec "$@"
