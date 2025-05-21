#!/bin/sh
set -e

# Tell Flask where the factory lives
export FLASK_APP=run.py           # your run.py already instantiates `app`

# Always bring the DB up to the latest revision
uv run flask db upgrade

# Hand over to whatever CMD the image was given
exec "$@"
