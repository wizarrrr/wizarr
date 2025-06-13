#!/usr/bin/env sh
set -eu

echo "[entrypoint] 🚀 Starting Wizarr container…"

# ───────── 1) Create or reuse the chosen UID/GID ──────────
PUID="${PUID:-1000}"
PGID="${PGID:-1000}"

if [ "$(id -u)" = "0" ]; then
  echo "[entrypoint] 👤 Wanted UID=$PUID  GID=$PGID"

  # Figure out which *names* already map to those numeric IDs
  EXISTING_USER="$(getent passwd "$PUID"  | cut -d: -f1 || true)"
  EXISTING_GRP="$(getent group  "$PGID"  | cut -d: -f1 || true)"

  # Decide what account we'll run as
  TARGET_USER="${EXISTING_USER:-wizarruser}"
  TARGET_GRP="${EXISTING_GRP:-wizarrgroup}"

  # Create group only if the GID isn't taken
  if [ -z "$EXISTING_GRP" ]; then
    addgroup -S -g "$PGID" "$TARGET_GRP"
  fi

  # Create user only if the UID isn't taken
  if [ -z "$EXISTING_USER" ]; then
    adduser  -S -G "$TARGET_GRP" -u "$PUID" "$TARGET_USER"
  else
    # Make sure the existing user is in the right group
    adduser "$EXISTING_USER" "$TARGET_GRP" || true
  fi

  # Fix ownership of bind-mounts
  chown -R "$TARGET_USER":"$TARGET_GRP" /data /.cache /opt/default_wizard_steps

  # Re-exec as that user
  exec su-exec "$TARGET_USER":"$TARGET_GRP" "$0" "$@"
fi

echo "[entrypoint] 👍 Running as $(id -un):$(id -gn) ($(id -u):$(id -g))"

# ─────────────────────────────────────────────────────────────────────────────
# 2) Seed wizard steps per-server
#
#   • For every directory inside $DEFAULT (e.g. plex/ jellyfin/ …) we check if
#     the matching subdir in $TARGET exists **and** contains at least one
#     visible file.  Only if it's empty (or missing) do we copy in the
#     defaults for that server type.  This allows users to customise the steps
#     for one media server without having to keep copies for all others.
# ─────────────────────────────────────────────────────────────────────────────

TARGET=/data/wizard_steps
DEFAULT=/opt/default_wizard_steps

# ensure both directories exist
mkdir -p "$TARGET"

if [ -d "$DEFAULT" ]; then
  for src in "$DEFAULT"/*; do
    [ -d "$src" ] || continue  # skip non-dirs
    name="$(basename "$src")"
    dst="$TARGET/$name"

    # The dst folder is considered "empty" if it has no regular files
    if [ ! -d "$dst" ] || [ -z "$(find "$dst" -type f -print -quit 2>/dev/null)" ]; then
      echo "[entrypoint] ✨ Seeding default wizard steps for $name…"
      mkdir -p "$dst"
      cp -a "$src/." "$dst/"
    else
      echo "[entrypoint] ↩️  Custom wizard steps for $name detected – keeping user files"
    fi
  done
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
