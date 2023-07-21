FROM python:3.11.4-alpine

WORKDIR /data
COPY . /data


RUN apk add --no-cache tzdata nodejs npm cargo && \
    pip3 install --no-cache --upgrade pip && \
    pip3 install --no-cache -r requirements.txt

WORKDIR /data/app/static

RUN npm ci
RUN npm run build

WORKDIR /data

EXPOSE 5690
CMD [ "gunicorn", "--workers",  "1" , "--bind", "0.0.0.0:5690", "-m", "007", "--log-level", "debug", "run:app" ]
