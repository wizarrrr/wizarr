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

VERSION = "1.5.0"


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
                           'fr': 'french',
                           'sv': 'swedish',
                           'pt': 'portuguese',
                           'nl': 'dutch',
                           'pt_BR': 'portuguese',
                           'lt': 'lithuanian',
                           # 'nb_NO': 'norwegian',
                           # 'es': 'spanish',
                           # 'it': 'italian',

                           }
app.config["BABEL_DEFAULT_LOCALE"] = "en"
app.config["BABEL_TRANSLATION_DIRECTORIES"] = ('./translations')

babel = Babel(app, locale_selector=get_locale)


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
    expires = DateTimeField(null=True)
    unlimited = BooleanField(null=True)


class Settings(BaseModel):
    key = CharField()
    value = CharField()


class Users(BaseModel):
    id = IntegerField(primary_key=True)
    token = CharField()
    username = CharField()
    email = CharField()
    code = CharField()


class Oauth(BaseModel):
    id = IntegerField(primary_key=True)
    url = CharField(null=True)

class SourcesToRemove(BaseModel):
    email = CharField()
    done = IntegerField()

# Below is Database Initialisation in case of new instance
database.create_tables([Invitations, Settings, Users, Oauth, SourcesToRemove])

if __name__ == "__main__":
    web.check_plex_credentials()
    app.run()
    
from app import admin, web, plex