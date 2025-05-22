#!/usr/bin/env sh
set -eu

# 1️⃣  one-off legacy migration (fast no-op on new installs)
uv run python -m app.legacy_migration.rename_legacy

# 2️⃣  Alembic migrations as usual
uv run flask db upgrade

# 3️⃣  Attempt moving legacy data to new tables
uv run python -m app.legacy_migration.import_legacy

# 4️⃣  start Gunicorn / Flask
exec "$@"
