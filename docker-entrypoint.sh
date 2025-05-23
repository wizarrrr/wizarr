#!/usr/bin/env sh
set -eu

# ─────────────────────────────────────────────────────────────────────────────
# 1) Seed wizard steps if the target is truly empty (no visible files at all)
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
# 2) Legacy DB rename + migrations + import
# ─────────────────────────────────────────────────────────────────────────────
echo "[entrypoint] 🔄 Renaming legacy database (if any)…"
uv run python -m app.legacy_migration.rename_legacy

echo "[entrypoint] 🔧 Applying alembic migrations…"
uv run flask db upgrade

echo "[entrypoint] 🗄️ Importing legacy data…"
uv run python -m app.legacy_migration.import_legacy

# ─────────────────────────────────────────────────────────────────────────────
# 3) Hand off to your CMD (e.g. gunicorn)
# ─────────────────────────────────────────────────────────────────────────────
exec "$@"
