FROM python:3.12-alpine
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
# Install curl separately so it remains available for healthcheck
RUN apk add --no-cache curl tzdata

# Set up the working directory
WORKDIR /data
COPY . /data

# Run uv sync
RUN uv sync --locked

RUN uv run pybabel compile -d app/translations

#Healthcheck 
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD curl -fs http://localhost:5690/health || exit 1

EXPOSE 5690

COPY wizard_steps /opt/default_wizard_steps

COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh
ENTRYPOINT ["docker-entrypoint.sh"]

CMD uv run gunicorn \
    --config gunicorn.conf.py \
    --preload \
    --workers 4 \
    --bind 0.0.0.0:5690 \
    --umask 007 \
    run:app
