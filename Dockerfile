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
CMD [ "gunicorn", "--workers",  "3" , "--bind", "0.0.0.0:5690", "-m", "007", "run:app" ]