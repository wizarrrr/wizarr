# Start from the official Python 3.12 Alpine image
FROM python:3.13-alpine

# Set default environment variables for user/group IDs
ENV PUID=1000
ENV PGID=1000

# Copy the UV binaries from the "astral-sh/uv" image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Install curl (for the HEALTHCHECK), tzdata (if you need timezones), nodejs (for npm), and su-exec for user switching
RUN apk add --no-cache curl tzdata nodejs npm su-exec

# ─── 2. Copy your application code ──────────────────────────────────────────

# Set up the working directory for our code. We'll put everything under /data.
WORKDIR /data

# Copy the entire build context (your source code) into /data.
COPY . /data

# ─── 3. Run your build steps (still as root) ───────────────────────────────

# We run the build steps as root first, because installing packages
# or building assets often needs root privileges.
RUN uv sync --locked
RUN uv run pybabel compile -d app/translations

RUN npm --prefix app/static/ install
RUN npm --prefix app/static/ run build:css

# Create directories that need to be writable
RUN mkdir -p /.cache

ARG APP_VERSION=dev
ENV APP_VERSION=${APP_VERSION}

# Healthcheck: curl to localhost:5690/health
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD curl -fs http://localhost:5690/health || exit 1

# Expose port 5690
EXPOSE 5690

# Copy any wizard steps into /opt
COPY wizard_steps /opt/default_wizard_steps

# Copy entrypoint script and make it executable
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Entrypoint and default CMD
ENTRYPOINT ["docker-entrypoint.sh"]

# By default we run Gunicorn under wizarruser
CMD ["uv", "run", "gunicorn", \
     "--config", "gunicorn.conf.py", \
     "--preload", \
     "--workers", "4", \
     "--bind", "0.0.0.0:5690", \
     "--umask", "007", \
     "run:app"]