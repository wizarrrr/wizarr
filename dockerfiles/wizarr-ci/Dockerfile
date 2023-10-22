# Build image for Docker Image
FROM --platform=$TARGETPLATFORM python:3.12.0

# Install system dependencies
RUN apt-get update && \
    apt-get install -y \
    nginx \
    nmap \
    toilet \
    curl \
    && apt-get clean

# Set directory for Wizarr Frontend
WORKDIR /wizarr/frontend

# Copy Wizarr Frontend
COPY ../../dist/apps/wizarr-frontend/ ./

# Set directory for Wizarr Backend tmp
WORKDIR /wizarr/backend

# Copy Wizarr Backend
COPY ../../dist/apps/wizarr-backend/ ./tmp/

# Unpack Wizarr Backend wizarr_backend-x.x.x.tar file into /wizarr
RUN tar -xvzf ./tmp/wizarr_backend-*.tar.gz -C ./tmp/ && \
    pip install ./tmp/wizarr_backend-*.whl

# Copy Wizarr Backend tmp
RUN mv ./tmp/wizarr_backend-*/wizarr_backend/* ./
RUN rm -rf ./tmp

# Copy Docker Entrypoint
COPY ../../dockerfiles/wizarr/docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# Copy Nginx configuration
COPY ../../files/nginx-main.conf /etc/nginx/conf.d/wizarr.conf
# RUN rm /etc/nginx/conf.d/default.conf

# Copy Bashrc File
COPY ../../files/.bashrc /root/.bashrc
RUN chmod +x /root/.bashrc

# Copy latest file
COPY ../../latest /

# Environment Variables
ENV DATABASE_DIR=/data/database
ENV LATEST_FILE=/latest

# Set Entrypoint
ENTRYPOINT ["/docker-entrypoint.sh"]
