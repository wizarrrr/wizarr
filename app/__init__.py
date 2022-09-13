from flask import Flask
from peewee import *
from flask_httpauth import HTTPBasicAuth
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
auth = HTTPBasicAuth()

users = {
    os.getenv("ADMIN_USERNAME"): os.getenv("ADMIN_PASSWORD")
}
@auth.verify_password
def verify_password(username, password):
    if username in users and \
            users.get(username) == password:
        return username


database = SqliteDatabase("./database/database.db")

class BaseModel(Model):
    class Meta:
        database = database

class Invitations(BaseModel):
    code = CharField()
    used = BooleanField()
    used_at = DateTimeField(null=True)
    created = DateTimeField()
    used_by = CharField(null=True)

# Below is Database Initialisation in case of new instance
def all_subclasses(base: type) -> list[type]:
    return [
        cls
        for sub in base.__subclasses__()
        for cls in [sub] + all_subclasses(sub)
    ]


try:
    models = [
        sub for sub in all_subclasses(Model)
        if not sub.__name__.startswith('_')
    ]

    database.create_tables(models)
except:
    pass

from app import web

if __name__ == "__main__":
    web.check_plex_credentials()
    app.run()