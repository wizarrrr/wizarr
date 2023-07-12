FROM python:3.11.3-alpine

WORKDIR /data
COPY . /data

RUN apk add --update nodejs npm

WORKDIR /data/app/static

RUN npm ci && npm install
RUN npm run build

WORKDIR /data

RUN apk add --no-cache tzdata && \
    pip3 install --no-cache --upgrade pip && \
    pip3 install --no-cache -r requirements.txt

EXPOSE 5690
CMD [ "gunicorn", "--workers",  "3" , "--bind", "0.0.0.0:5690", "-m", "007", "run:app" ]
