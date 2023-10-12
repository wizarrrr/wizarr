#!/bin/bash

# Set the name and tag for the image
IMAGE_NAME="wizarrrr/wizarr"
IMAGE_TAG="v3-beta"

# Create a buildx environment
docker buildx create --name wizarrbuilder
docker buildx use wizarrbuilder

# Build the image using buildx
docker buildx build --platform linux/386,linux/amd64,linux/arm/v5,linux/arm/v7,linux/arm64/v8,linux/mips64le,linux/ppc64le,linux/s390x --cache-to type=local,dest=database/cache --push -t $IMAGE_NAME:$IMAGE_TAG -t $IMAGE_NAME:$IMAGE_TAG-3.4.2 --progress tty .

# Remove the buildx environment
docker buildx rm wizarrbuilder

