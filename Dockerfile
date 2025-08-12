# ─── Stage 1: Dependencies ───────────────────────────────────────────────
FROM python:3.12-alpine AS deps

# Copy the UV binaries from the "astral-sh/uv" image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Install system dependencies
RUN apk add --no-cache nodejs npm

# Set working directory
WORKDIR /data

# Copy dependency files first for better caching
COPY pyproject.toml uv.lock ./
COPY app/static/package*.json ./app/static/

# Install Python dependencies
RUN uv sync --locked

# Install npm dependencies
RUN npm --prefix app/static/ install

# ─── Stage 2: Build assets ────────────────────────────────────────────────
FROM deps AS builder

# Copy source files needed for building
COPY app/ ./app/
COPY babel.cfg ./

# Build translations
RUN uv run pybabel compile -d app/translations

# Build static assets
RUN npm --prefix app/static/ run build

# ─── Stage 3: Runtime ─────────────────────────────────────────────────────
FROM python:3.12-alpine

# Set default environment variables for user/group IDs
ENV PUID=1000
ENV PGID=1000

# Copy the UV binaries
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Install runtime dependencies only
RUN apk add --no-cache curl tzdata su-exec

# Set working directory
WORKDIR /data

# Copy Python environment from deps stage
COPY --from=deps /data/.venv /data/.venv

# Copy application code and built assets
COPY --chown=1000:1000 --from=builder /data/app /data/app
COPY --chown=1000:1000 . /data

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