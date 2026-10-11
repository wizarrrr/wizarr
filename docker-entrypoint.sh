#!/usr/bin/env sh
set -eu

echo "[entrypoint] 🚀 Starting Wizarr container…"

# ───────── 1) Create or reuse the chosen UID/GID ──────────
DEFAULT_UID='1000'
DEFAULT_GID='1000'
PUID="${PUID:-$DEFAULT_UID}"
PGID="${PGID:-$DEFAULT_GID}"

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

  # Ensure critical data directories exist
  mkdir -p /data/database

  # Only recurse into bind mount directories and cache
  echo "[entrypoint] ⚙️  Fixing ownership for bind mounts…"
  chown -R "$TARGET_USER":"$TARGET_GRP" \
    /data/database /.cache /opt/default_wizard_steps


  # Fix ownership of bind-mounts (only persistent data directories)
  if [ "$PUID:$PGID" != "$DEFAULT_UID:$DEFAULT_GID" ]; then
    echo "[entrypoint] ⚙️  Fixing ownership for custom UID/GID…"

    # Fix ownership of persistent user data only
    [ -d /data/database ] && chown -R "$PUID":"$PGID" /data/database
  else
    echo "[entrypoint] ⚙️  Default UID/GID; skipping chown."
  fi

  # Re-exec as that user
  exec su-exec "$TARGET_USER":"$TARGET_GRP" "$0" "$@"
fi

echo "[entrypoint] 👍 Running as $(id -un):$(id -gn) ($(id -u):$(id -g))"

# ─────────────────────────────────────────────────────────────────────────────
# 3) DB Migrations
# ─────────────────────────────────────────────────────────────────────────────

echo "[entrypoint] 🔧 Applying alembic migrations…"
FLASK_SKIP_SCHEDULER=true uv run --frozen --no-dev flask db upgrade

# ─────────────────────────────────────────────────────────────────────────────
# 4) Hand off to your CMD (e.g. gunicorn)
# ─────────────────────────────────────────────────────────────────────────────
exec "$@"
