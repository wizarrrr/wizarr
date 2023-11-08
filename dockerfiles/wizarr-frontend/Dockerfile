# Build image for Docker Image
FROM --platform=$TARGETPLATFORM node:18.18.2 AS base

# Set directory for Wizarr Frontend
WORKDIR /wizarr-build
COPY ../../ ./

# Set environment variables for NPM Version
ENV NPM_CONFIG_LOGLEVEL=warn \
    NODE_VERSION=18.18.2

# Install dependencies
RUN npm install -g npm@9.8.1 && \
    npm install

# Build Wizarr Frontend
RUN npx nx build wizarr-frontend

# Final image for Docker Image
FROM --platform=$TARGETPLATFORM nginx:stable AS final

# Install system dependencies
RUN apt-get update && \
    apt-get install -y \
    toilet \
    figlet \
    && apt-get clean

# Set directory for Wizarr Frontend
WORKDIR /wizarr

# Copy Wizarr Frontend
COPY --from=base /wizarr-build/dist/apps/wizarr-frontend/ ./

# Copy Nginx configuration
COPY ../../files/nginx-frontend.conf /etc/nginx/conf.d/wizarr.conf
RUN rm -f /etc/nginx/conf.d/default.conf /etc/nginx/sites-enabled/default

# Copy Docker Entrypoint
COPY ../../dockerfiles/wizarr-frontend/docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# Copy Bashrc File
COPY ../../files/.bashrc /root/.bashrc
RUN chmod +x /root/.bashrc

# Copy latest file
COPY ../../latest /

# Environment Variables
ENV LATEST_FILE=/latest

# Expose Ports
EXPOSE 5690

# Set Entrypoint
ENTRYPOINT ["/docker-entrypoint.sh"]