FROM python:3.12-alpine
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

RUN apk add --no-cache curl tzdata


#ENV PATH="/usr/local/bin:${PATH}"

# now create your non-root user
RUN addgroup -S wizarr \
 && adduser  -S wizarr -G wizarr

WORKDIR /data
COPY --chown=wizarr:wizarr . /data

USER wizarr
RUN uv sync --locked \
 && mkdir -p /data/config \
 && chown -R wizarr:wizarr /data

USER wizarr
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD curl -fs http://localhost:5690/health || exit 1

EXPOSE 5690
ENTRYPOINT ["sh","-c","set -eu; uv run python -m app.legacy_migration.rename_legacy; uv run flask db upgrade; uv run python -m app.legacy_migration.import_legacy; exec \"$@\"","--"]
CMD ["uv","run","gunicorn","--config","gunicorn.conf.py","--preload","--workers","4","--bind","0.0.0.0:5690","--umask","007","run:app"]
