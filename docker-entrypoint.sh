#!/bin/sh
set -e

# The migrations folder is already inside the image.
# Just apply whatever's new:
uv run flask db upgrade

exec "$@"        # hand off to gunicorn