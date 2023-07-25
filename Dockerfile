FROM python:3.11.4-alpine

WORKDIR /data
COPY . /data


RUN apk add tzdata nodejs npm cargo
RUN pip3 install --upgrade pip
RUN pip3 install -r requirements.txt

WORKDIR /data/app/static

RUN npm install
RUN npm run build

WORKDIR /data

EXPOSE 5690
CMD [ "gunicorn", "--workers",  "1" , "--bind", "0.0.0.0:5690", "-m", "007", "--log-level", "debug", "run:app" ]
