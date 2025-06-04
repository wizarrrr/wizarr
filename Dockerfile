# Start from the official Python 3.12 Alpine image
FROM python:3.12-alpine

# Copy the UV binaries from the "astral-sh/uv" image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Install curl (for the HEALTHCHECK), tzdata (if you need timezones), and nodejs (for npm)
RUN apk add --no-cache curl tzdata nodejs npm

# ─── 1. Create a non-root user and group ────────────────────────────────────

# Create a group called "wizarrgroup" and a user "wizarruser" in that group.
# - -S flag means "system" (no encrypted password, no login shell).
# -G flag adds the user to the group.
#
# We’ll choose UID 1000 / GID 1000 as an example, but you can change those
# to whatever you like (or leave them out, and Alpine will pick UID/GID ≥1000).
RUN addgroup -S wizarrgroup && \
    adduser -S -G wizarrgroup -u 1000 wizarruser

# ─── 2. Copy your application code ──────────────────────────────────────────

# Set up the working directory for our code. We’ll put everything under /data.
WORKDIR /data

# Copy the entire build context (your source code) into /data.
COPY . /data



# If you also have files under /opt/default_wizard_steps, make sure that
# wizarruser can access them too. We’ll adjust ownership after we copy them below.

# ─── 3. Run your build steps (still as root) ───────────────────────────────

# We run the build steps as root first, because installing packages
# or building assets often needs root privileges.
RUN uv sync --locked
RUN uv run pybabel compile -d app/translations

RUN npm --prefix app/static/ install

# Ensure that "wizarruser" owns everything in /data, so it can read/write if needed.
# If your code needs to write to /data (e.g. logs, caches), this is essential.
RUN chown -R wizarruser:wizarrgroup /data

RUN mkdir /.cache
RUN chown -R wizarruser:wizarrgroup /.cache


ARG APP_VERSION=dev
ENV APP_VERSION=${APP_VERSION}

# ─── 4. Copy extra files and fix ownership ─────────────────────────────────

# Healthcheck: curl to localhost:5690/health
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD curl -fs http://localhost:5690/health || exit 1

# Expose port 5690
EXPOSE 5690

# Copy any wizard steps into /opt and chown them for wizarruser
COPY wizard_steps /opt/default_wizard_steps
RUN chown -R wizarruser:wizarrgroup /opt/default_wizard_steps

# Copy entrypoint script and make it executable
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh && \
    chown wizarruser:wizarrgroup /usr/local/bin/docker-entrypoint.sh

# ─── 5. Switch to non-root user ─────────────────────────────────────────────

# From now on, everything will run as "wizarruser" (UID 1000).
#
# If someone does `docker run --user 2000:3000 ...`,
# Docker will override this and run as UID 2000 inside the container.
USER wizarruser

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