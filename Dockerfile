FROM python:3.12-alpine

# Install runtime and build dependencies
RUN apk add --no-cache --virtual .build-deps curl && \
    curl -fsSL https://astral.sh/uv/install.sh -o /uv-installer.sh && \
    sh /uv-installer.sh && \
    rm /uv-installer.sh && \
    apk del .build-deps && \
    apk add --no-cache tzdata

# Ensure the installed binary is on the `PATH`
ENV PATH="/root/.local/bin/:$PATH"

WORKDIR /data
COPY . /data

# Run uv sync
RUN uv sync --locked

#Healthcheck 
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD curl -fs http://localhost:5690/health || exit 1


EXPOSE 5690

COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh
ENTRYPOINT ["docker-entrypoint.sh"]

CMD [
  "uv", "run", "gunicorn",
  "--config", "gunicorn.conf.py",
  "--preload",
  "--workers", "4",
  "--bind", "0.0.0.0:5690",
  "--umask", "007",
  "run:app"
]