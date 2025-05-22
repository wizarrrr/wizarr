FROM python:3.12-alpine

# Install curl separately so it remains available for healthcheck
RUN apk add --no-cache curl tzdata

# Install build dependencies for uv installation
RUN apk add --no-cache --virtual .build-deps && \
    curl -fsSL https://astral.sh/uv/install.sh -o /uv-installer.sh && \
    sh /uv-installer.sh && \
    rm /uv-installer.sh && \
    apk del .build-deps

# Ensure the installed binary is on the `PATH`
ENV PATH="/root/.local/bin/:$PATH"

# Create non-root user and group
RUN addgroup -S wizarr && adduser -S wizarr -G wizarr

WORKDIR /data

# Copy files and set proper permissions
COPY --chown=wizarr:wizarr . /data

# Run uv sync
RUN uv sync --locked && \
    # Create necessary directories with proper permissions
    mkdir -p /data/config && \
    chown -R wizarr:wizarr /data

#Healthcheck 
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD curl -fs http://localhost:5690/health || exit 1

EXPOSE 5690


# Switch to non-root user
USER wizarr

ENTRYPOINT ["sh", "-c", "set -eu; uv run python -m app.legacy_migration.rename_legacy; uv run flask db upgrade; uv run python -m app.legacy_migration.import_legacy; exec \"$@\"", "--"]
CMD uv run gunicorn \
    --config gunicorn.conf.py \
    --preload \
    --workers 4 \
    --bind 0.0.0.0:5690 \
    --umask 007 \
    run:app
