# Use an official Node.js runtime as the base image
FROM --platform=linux/amd64 node:14.21.3

# Install dependencies
RUN apt-get update && apt-get install -y libc6-dev build-essential && apt-get clean

# Set the working directory inside the container
WORKDIR /app

# Copy package.json and package-lock.json to the working directory
COPY . .

# Install application dependencies using Yarn
RUN yarn install

# Build the application
RUN yarn build

# Expose the port that the application will run on
EXPOSE 9000

# Define the command to start your application
CMD [ "yarn", "serve" ]
