#!/bin/bash

# Start Nginx in the background
nginx

# Start Gunicorn with the specified worker and bind settings
gunicorn --worker-class geventwebsocket.gunicorn.workers.GeventWebSocketWorker --bind 0.0.0.0:5000 -m 007 run:app

# Keep the script running to prevent the container from exiting
tail -f /dev/null
