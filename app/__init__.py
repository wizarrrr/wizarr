

from flask import Flask, request, session
from peewee import *
from playhouse.migrate import *
from flask_babel import Babel
import os
from dotenv import load_dotenv
from flask_session import Session
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration

load_dotenv()

app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True

app.config["SESSION_TYPE"] = "filesystem"
app.config["SESSION_FILE_DIR"] = "./database/sessions"
Session(app)

VERSION = "0.11.0"

# Bug Reporting Stuff
if os.getenv("ALLOW_BUG_REPORTING") == "true":
    sentry_sdk.init(
        dsn="https://1ce2ff6a6de6495cb8045ea2f64b924c@o1419304.ingest.sentry.io/6763170",
        integrations=[
            FlaskIntegration(),
        ],

        # Set traces_sample_rate to 1.0 to capture 100%
        # of transactions for performance monitoring.
        # We recommend adjusting this value in production.
        traces_sample_rate=1.0
    )

# Translation stuff
base_dir = os.path.abspath(os.path.dirname(__file__))
app.config["LANGUAGES"] = {'en': 'english', 'fr': 'french'}
app.config["BABEL_TRANSLATION_DIRECTORIES"] = os.path.join(
    base_dir, "app/translations")
babel = Babel(app)


@babel.localeselector
def get_locale():
    return 'fr'


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


# Security Feature, prevent Wizarr From starting if OS.GETENV set

if os.getenv("ADMIN_USERNAME"):
    print("Admin username is set in the .env file. This has been deprecated and for security reasons, I have exited your app. Please consult the Github repo!")
    exit()


# Add Expires if not existing. WILL BE REMOVED IN FUTURE VERSIONS

try:
    Invitations.get_or_none(Invitations.unlimited == 0)
except:
    try:
        migrator = SqliteMigrator(database)
        migrate(
            migrator.add_column('Invitations', 'unlimited', Invitations.unlimited),)
    except:
        pass

# Below is Database Initialisation in case of new instance
database.create_tables([Invitations, Settings])

if __name__ == "__main__":
    web.check_plex_credentials()
    app.run()
from app import admin, web
