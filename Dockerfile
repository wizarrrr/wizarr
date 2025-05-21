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


EXPOSE 5690

COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh
ENTRYPOINT ["docker-entrypoint.sh"]
CMD [ "uv", "run", "gunicorn", "--workers",  "4" , "--bind", "0.0.0.0:5690", "-m", "007", "run:app" ]