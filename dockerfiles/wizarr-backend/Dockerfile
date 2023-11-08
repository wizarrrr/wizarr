# Build image for Docker Image
FROM --platform=$TARGETPLATFORM nikolaik/python-nodejs:python3.12-nodejs18 AS base

# Set directory for Wizarr Backend
WORKDIR /wizarr-build
COPY ../../ ./

# Set environment variables for NPM Version
ENV NPM_CONFIG_LOGLEVEL=warn \
    NODE_VERSION=18.18.2

# Set environment variables for Poetry Version
ENV PIP_DEFAULT_TIMEOUT=100 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    POETRY_VERSION=1.6.1

# Install dependencies
RUN pip install "poetry==$POETRY_VERSION"

# Install dependencies
RUN npm install -g npm@9.8.1 && \
    npm install

# Build Wizarr Backend
RUN npx nx build wizarr-backend

# Final image for Docker Image
FROM --platform=$TARGETPLATFORM python:3.12.0 AS final

# Install system dependencies
RUN apt-get update && \
    apt-get install -y \
    nginx \
    nmap \
    toilet \
    figlet \
    curl \
    && apt-get clean

# Set directory for Wizarr Backend tmp
WORKDIR /wizarr/tmp

# Copy Wizarr Backend
COPY --from=base /wizarr-build/dist/apps/wizarr-backend/ ./

# Unpack Wizarr Backend wizarr_backend-x.x.x.tar file into /wizarr
RUN tar -xvzf ./wizarr_backend-*.tar.gz -C ./ && \
    pip install ./wizarr_backend-*.whl

# Set directory for Wizarr Backend
WORKDIR /wizarr

# Copy Wizarr Backend tmp
RUN mv ./tmp/wizarr_backend-*/wizarr_backend/* ./
RUN rm -rf ./tmp

# Copy Docker Entrypoint
COPY ../../dockerfiles/wizarr-backend/docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# Copy Nginx configuration
COPY ../../files/nginx-backend.conf /etc/nginx/conf.d/wizarr.conf
RUN rm -f /etc/nginx/conf.d/default.conf /etc/nginx/sites-enabled/default

# Copy Bashrc File
COPY ../../files/.bashrc /root/.bashrc
RUN chmod +x /root/.bashrc

# Copy latest file
COPY ../../latest /

# Environment Variables
ENV DATABASE_DIR=/data/database
ENV LATEST_FILE=/latest

# Expose Ports
EXPOSE 5690

# Set Entrypoint
ENTRYPOINT ["/docker-entrypoint.sh"]
