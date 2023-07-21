FROM python:3.11.4-alpine

WORKDIR /data
COPY . /data

RUN apk add tzdata libffi-dev gcc python3-dev musl-dev g++ make openssl-dev

RUN pip3 install --upgrade pip setuptools wheel
RUN pip3 install -r requirements.txt

RUN apk add --update nodejs npm

WORKDIR /data/app/static

RUN npm ci
RUN npm run build

WORKDIR /data

EXPOSE 5690
CMD [ "gunicorn", "--workers",  "1" , "--bind", "0.0.0.0:5690", "-m", "007", "--log-level", "debug", "run:app" ]
