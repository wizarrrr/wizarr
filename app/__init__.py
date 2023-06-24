from flask import Flask, request, session
from peewee import *
from playhouse.migrate import *
from flask_babel import Babel
import os
from dotenv import load_dotenv
from flask_session import Session
from flask_apscheduler import APScheduler
from flask_htmx import HTMX

load_dotenv()

app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True

app.config["SESSION_TYPE"] = "filesystem"
app.config["SESSION_FILE_DIR"] = "./database/sessions"
Session(app)
htmx = HTMX(app)

VERSION = "2.2.0"


def get_locale():
    if os.getenv("FORCE_LANGUAGE"):
        return os.getenv("FORCE_LANGUAGE")
    elif request.args.get('lang'):
        session['lang'] = request.args.get('lang')
        return session.get('lang', 'en')
    else:
        return request.accept_languages.best_match(app.config['LANGUAGES'].keys())


# Translation stuff
base_dir = os.path.abspath(os.path.dirname(__file__))
app.config["LANGUAGES"] = {'en': 'english',
                           'de': 'german',
                           'zh': 'chinese',
                           'fr': 'french',
                           'sv': 'swedish',
                           'pt': 'portuguese',
                           # 'nl': 'dutch',
                           'pt_BR': 'portuguese',
                           'lt': 'lithuanian',
                           # 'nb_NO': 'norwegian',
                           'es': 'spanish',
                           # 'it': 'italian',
                           'ca': 'catalan',
                           'pl': 'polish',

                           }
app.config["BABEL_DEFAULT_LOCALE"] = "en"
app.config["BABEL_TRANSLATION_DIRECTORIES"] = ('./translations')

# Translation
babel = Babel(app, locale_selector=get_locale)

# Scheduler
app.config["SCHEDULER_API_ENABLED"] = True
scheduler = APScheduler()
scheduler.init_app(app)
scheduler.start()

# Database stuff
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
    expires = DateTimeField(null=True)  # How long the invite is valid for
    unlimited = BooleanField(null=True)
    duration = CharField(null=True)  # How long the membership is kept for
    specific_libraries = CharField(null=True)
    plex_allow_sync = BooleanField(null=True)
    plex_home = BooleanField(null=True)


class Settings(BaseModel):
    key = CharField()
    value = CharField(null=True)


class Users(BaseModel):
    id = IntegerField(primary_key=True)
    token = CharField()  # Plex ID or Jellyfin ID
    username = CharField()
    email = CharField()
    code = CharField()
    expires = DateTimeField(null=True)
    auth = CharField(null=True)


class Notifications(BaseModel):
    id = IntegerField(primary_key=True)
    name = CharField()
    type = CharField()
    url = CharField()
    username = CharField(null=True)
    password = CharField(null=True)


# Below is Database Initialisation in case of new instance
database.create_tables(
    [Invitations, Settings, Users, Notifications], safe=True)

if __name__ == "__main__":
    app.run()

from app import admin, web, plex, tasks, jellyfin, helpers, universal, notifications, mediarequest
