from flask import Flask, request, session
from peewee import *
from playhouse.migrate import *
from flask_babel import Babel
import os
from dotenv import load_dotenv
from flask_session import Session
from flask_apscheduler import APScheduler


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


#Translation
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
    expires = DateTimeField(null=True) #How long the invite is valid for
    unlimited = BooleanField(null=True)
    duration = CharField(null=True) #How long the membership is kept for
    specific_libraries = CharField(null=True)


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

class ExpiringInvitations(BaseModel):
    code = CharField()
    created = DateTimeField()
    used_by = CharField()
    expires = DateTimeField(null=True)

# Below is Database Initialisation in case of new instance
database.create_tables([Invitations, Settings, Users, Oauth, ExpiringInvitations])

# Migrations 1
try:
    migrator = SqliteMigrator(database)
    duration = CharField(null=True) #Add Duration after update
    migrate(
        migrator.add_column('Invitations', 'duration', duration)
    )
except:
    pass


# Migrations 2
try:
    migrator = SqliteMigrator(database)
    specific_libraries = CharField(null=True) #Add Duration after update
    migrate(
        migrator.add_column('Invitations', 'specific_libraries', specific_libraries)
    )
except:
    pass

# Migrations 2
try:

    if ExpiringInvitations.used_by == IntegerField():
        migrator = SqliteMigrator(database)
        used_by = CharField(null=True) #Add Duration after update
        migrate(
            migrator.drop_column('Invitations', 'used_by'),
            migrator.add_column('Invitations', 'used_by', used_by)
        )
except:
    pass

if __name__ == "__main__":
    web.check_plex_credentials()
    app.run()


from app import admin, web, plex