
from flask import Flask, request, session
from peewee import *
from playhouse.migrate import *
from flask_babel import Babel
import os
from dotenv import load_dotenv
from flask_session import Session

load_dotenv()

app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True

app.config["SESSION_TYPE"] = "filesystem"
app.config["SESSION_FILE_DIR"] = "./database/sessions"
Session(app)

VERSION = "0.10.3"

#Translation stuff
babel = Babel(app)

app.config["LANGUAGES"] = ['en', 'fr']

@babel.localeselector
def get_locale():
    return request.accept_languages.best_match(app.config['LANGUAGES'])


#Database stuff
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
    expires = DateTimeField(null=True)


class Settings(BaseModel):
    key = CharField()
    value = CharField()


# Security Feature, prevent Wizarr From starting if OS.GETENV set

if os.getenv("ADMIN_USERNAME"):
    print("Admin username is set in the .env file. This has been deprecated and for security reasons, I have exited your app. Please consult the Github repo!")
    exit()


# Add Expires if not existing. WILL BE REMOVED IN FUTURE VERSIONS
try:
    Invitations.get_or_none(Invitations.expires == None)
except:
    try:
        migrator = SqliteMigrator(database)
        migrate(
            migrator.add_column('Invitations', 'expires', Invitations.expires),
        )
    except:
        pass


# Below is Database Initialisation in case of new instance
database.create_tables([Invitations, Settings])

if __name__ == "__main__":
    web.check_plex_credentials()
    app.run()

from app import admin, web