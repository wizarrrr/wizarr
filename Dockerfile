FROM python:3.11.3-alpine

WORKDIR /data
COPY . /data

RUN apk add --update nodejs npm

WORKDIR /data/app/static

RUN npm ci && npm install
RUN npm run build

WORKDIR /data

RUN apk add tzdata libffi-dev gcc python3-dev musl-dev
RUN pip3 install --upgrade pip setuptools
RUN pip3 install -r requirements.txt

EXPOSE 5690
CMD [ "gunicorn", "--workers",  "3" , "--bind", "0.0.0.0:5690", "-m", "007", "run:app" ]
