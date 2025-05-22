FROM python:3.12-alpine
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
# Install curl separately so it remains available for healthcheck
RUN apk add --no-cache curl tzdata



# Create a non-root user and group
RUN addgroup -S wizarrgroup && adduser -S wizarruser -G wizarrgroup

# Set up the working directory
WORKDIR /data
COPY . /data

# Run uv sync
RUN uv sync --locked

# Ensure proper permissions
RUN chown -R wizarruser:wizarrgroup /data && \
    mkdir -p /home/wizarruser/.local/bin && \
    chown -R wizarruser:wizarrgroup /home/wizarruser

# Ensure the installed binary is on the `PATH`
#ENV PATH="/root/.local/bin:/home/wizarruser/.local/bin:$PATH"

# Switch to non-root user
USER wizarruser

#Healthcheck 
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD curl -fs http://localhost:5690/health || exit 1

EXPOSE 5690

ENTRYPOINT ["sh", "-c", "set -eu; uv run python -m app.legacy_migration.rename_legacy; uv run flask db upgrade; uv run python -m app.legacy_migration.import_legacy; exec \"$@\"", "--"]

CMD uv run gunicorn \
    --config gunicorn.conf.py \
    --preload \
    --workers 4 \
    --bind 0.0.0.0:5690 \
    --umask 007 \
    run:app
