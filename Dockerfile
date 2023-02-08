FROM python:3.11.2-alpine
RUN apk add --no-cache tzdata
RUN mkdir /data
WORKDIR /data
COPY requirements.txt requirements.txt
RUN pip install --upgrade pip
RUN pip install -r requirements.txt
COPY . /data
CMD [ "gunicorn", "--workers",  "3" , "--bind", "0.0.0.0:5690", "-m", "007", "run:app" ]
EXPOSE 5690