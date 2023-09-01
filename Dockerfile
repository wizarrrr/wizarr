FROM python:3.11.4-alpine

# Copy everything to /data
COPY . /data

# Update the system
RUN apk update

# Setup Nginx Environment
RUN apk add --no-cache nginx
COPY nginx.conf /etc/nginx/nginx.conf

# Setup Python Environment
WORKDIR /data/backend
RUN apk add tzdata cargo libffi-dev openssl-dev nmap tzdata
RUN pip3 install --upgrade pip
RUN pip3 install -r requirements.txt

# Setup Node Environment
RUN apk add nodejs npm
RUN npm install -g npm@latest

# Build Frontend Environment
WORKDIR /data/frontend
RUN npm install
RUN npm run build

# Setup Timezone
ENV TZ UTC
RUN cp /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Start B
WORKDIR /data/backend
CMD [ "nginx", "-g", "daemon off;", "gunicorn", "--worker-class", "geventwebsocket.gunicorn.workers GeventWebSocketWorker", "--bind", "0.0.0.0:5690", "-m", "007", "run:app" ]

EXPOSE 5690