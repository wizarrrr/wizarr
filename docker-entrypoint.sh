#!/usr/bin/env sh
set -eu

# ── 1) Seed wizard steps if the bind‐mount is empty
if [ -d /data/wizard_steps ] && [ -z "$(ls -A /data/wizard_steps)" ]; then
  echo "[entrypoint] seeding default wizard steps…"
  cp -r /opt/default_wizard_steps/* /data/wizard_steps/
fi

# ── 2) Legacy DB rename + import + schema upgrade
echo "[entrypoint] renaming legacy DB…"
uv run python -m app.legacy_migration.rename_legacy

echo "[entrypoint] applying alembic migrations…"
uv run flask db upgrade

echo "[entrypoint] importing legacy data…"
uv run python -m app.legacy_migration.import_legacy

# ── 3) Finally, hand off to the main CMD (e.g. gunicorn)
exec "$@"
