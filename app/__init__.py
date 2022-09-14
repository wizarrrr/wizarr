from flask import Flask, redirect
from peewee import *
from flask_httpauth import HTTPBasicAuth
import os
from dotenv import load_dotenv
from werkzeug.security import check_password_hash

load_dotenv()

app = Flask(__name__)
auth = HTTPBasicAuth()
app.config["TEMPLATES_AUTO_RELOAD"] = True
VERSION = "0.3.0"

@auth.verify_password
def verify_password(username, password):
    if os.getenv("ADMIN_USERNAME") == username:
        if os.getenv("ADMIN_PASSWORD") == password:
            print("WARNING! Environment variables are being used. This is being DEPRECATED in future versions. Visit /settings to set up a new admin account and see Documentation for update details.")
            return username
    elif Settings.select().where(Settings.key == 'admin_username').exists():
        if username == Settings.select().where(Settings.key == 'admin_username').get().value:
            if check_password_hash(Settings.select().where(Settings.key == 'admin_password').get().value, password):
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

class Settings(BaseModel):
    key = CharField()
    value = CharField()

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

from app import admin, web

if __name__ == "__main__":
    web.check_plex_credentials()
    app.run()