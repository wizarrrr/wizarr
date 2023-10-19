# Build Stage
FROM --platform=$TARGETPLATFORM python:3.12.0 AS build

# Set environment variables
ARG TARGETPLATFORM
ARG BUILDPLATFORM

# Show buld platform and target platform in Docker log
RUN echo "Build platform is $BUILDPLATFORM" && echo "Target platform is $TARGETPLATFORM"

# Update system and install build dependencies
RUN apt-get update && apt-get install -y libffi-dev g++ nmap nginx figlet curl nodejs npm && apt-get clean

# Copy over version
WORKDIR /data
COPY latest latest

#######################
# Backend Build Stage #
#######################

# Copy only the necessary files for building
WORKDIR /data/backend
COPY ./backend ./

# Install build dependencies
# RUN apk add --no-cache libffi-dev g++ nmap tzdata nginx bash figlet

# Copy .bashrc from ./files to ~/.bashrc
COPY ./files/.bashrc /root/.bashrc

# Upgrade pip and install Python dependencies
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt


########################
# Frontend Build Stage #
########################

# Copy only the necessary files for building
WORKDIR /data/frontend
COPY ./frontend/ ./

# Node.js and Frontend build
RUN npm install --verbose
RUN npm run build


#################
# Runtime Stage #
#################

WORKDIR /data

# Copy Nginx configuration
COPY nginx.conf /etc/nginx/sites-available/wizarr.conf
RUN ln -s /etc/nginx/sites-available/wizarr.conf /etc/nginx/sites-enabled/wizarr.conf

# Setup timezone
# RUN cp /usr/share/zoneinfo/UTC /etc/localtime \
#     && echo UTC > /etc/timezone

# Set environment variables
ENV TZ=Etc/UTC

# Expose ports
EXPOSE 5690

COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# Start Nginx in the background and Gunicorn in the foreground
ENTRYPOINT ["/docker-entrypoint.sh"]

LABEL org.opencontainers.image.authors "Ashley Bailey <admin@ashleybailey.me>"
LABEL org.opencontainers.image.description "Wizarr is an advanced user invitation and management system for Jellyfin, Plex, Emby etc."

LABEL org.label-schema.schema-version="1.0" \
    org.label-schema.license="MIT" \
    org.label-schema.name="wizarr" \
    org.label-schema.description="Wizarr is an advanced user invitation and management system for Jellyfin, Plex, Emby etc." \
    org.label-schema.url="https://github.com/wizarrrr/wizarr" \
    org.label-schema.vcs-url="https://github.com/wizarrrr/wizarr.git" \
    maintainer="Ashley Bailey <admin@ashleybailey.me>" \
    description="Wizarr is an advanced user invitation and management system for Jellyfin, Plex, Emby etc."
