from datetime import timedelta
from json import dumps
from os import environ, getenv, path

from dotenv import load_dotenv
from flask import Flask
from packaging import version
from requests import get

from .logging import *
from .extensions import *
from .filters import *
from .security import *

from flask_sse import ServerSentEvents
from migrations import migrate
from models import *
from api import *


# Global App Version
VERSION = "3.0.0"
BASE_DIR = path.abspath(path.dirname(__file__))

# Load environment variables
load_dotenv()

# Initialize the app and api
app = Flask(__name__)

# Run database migrations scripts
migrate()

# Stop the app if the APP_URL is not set
# if not getenv("APP_URL"):
#     error("APP_URL not set or wrong format. See docs for more debug.")
#     exit(1)

# Add version to environment variables
environ["VERSION"] = VERSION

# Helper functions
# Check for updates
def need_update():
    try:
        return version.parse(VERSION) < version.parse(get("https://raw.githubusercontent.com/Wizarrrr/wizarr/master/.github/latest", timeout=100).content.decode("utf-8"))
    except Exception: return False

def is_beta():
    try:
        return version.parse(VERSION) > version.parse(get("https://raw.githubusercontent.com/Wizarrrr/wizarr/master/.github/latest", timeout=100).content.decode("utf-8"))
    except Exception: return False


# Set global variables for Jinja2 templates
app.jinja_env.globals.update(APP_NAME="Wizarr")
app.jinja_env.globals.update(APP_VERSION=VERSION)
app.jinja_env.globals.update(APP_GITHUB_URL="https://github.com/Wizarrrr/wizarr")
app.jinja_env.globals.update(APP_RELEASED="Beta" if is_beta() else "Stable")
app.jinja_env.globals.update(APP_LANG="en")
app.jinja_env.globals.update(APP_UPDATE=need_update())
app.jinja_env.globals.update(DISABLE_BUILTIN_AUTH=True if getenv("DISABLE_BUILTIN_AUTH", "false") == "true" else False)

# Set config variables for Flask
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.config["SESSION_TYPE"] = "filesystem"
app.config["SESSION_FILE_DIR"] = path.abspath(path.join(BASE_DIR, "../", "database", "sessions"))
app.config["LANGUAGES"] = {"en": "english", "de": "german", "zh": "chinese", "fr": "french", "sv": "swedish", "pt": "portuguese", "pt_BR": "portuguese", "lt": "lithuanian", "es": "spanish", "ca": "catalan", "pl": "polish" }
app.config["BABEL_DEFAULT_LOCALE"] = "en"
app.config["BABEL_TRANSLATION_DIRECTORIES"] = "./translations"
app.config["SCHEDULER_API_ENABLED"] = True
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=5)
app.config["UPLOAD_FOLDER"] = path.join(BASE_DIR, "../", "database", "uploads")
app.config["SWAGGER_UI_DOC_EXPANSION"] = "list"
app.config["SERVER_NAME"] = getenv("APP_URL")
app.config["APPLICATION_ROOT"] = "/"
app.config["PREFERRED_URL_SCHEME"] = "https" if getenv("HTTPS", "false") == "true" else "http"
app.config["JWT_SECRET_KEY"] = secret_key()
app.config["JWT_BLACKLIST_ENABLED"] = True
app.config["JWT_TOKEN_LOCATION"] = ["headers", "cookies", "json", "query_string"]
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=1)
app.config["JWT_COOKIE_CSRF_PROTECT"] = True
app.config["JWT_COOKIE_SECURE"] = True if app.debug is False else False

sse = ServerSentEvents()

# Initialize App Extensions
sess.init_app(app)
htmx.init_app(app)
babel.init_app(app)
jwt.init_app(app)
cache.init_app(app)
api.init_app(app)

# Register Jinja2 filters
app.add_template_filter(format_datetime)
app.add_template_filter(date_format)

# Register Flask blueprints
app.after_request(refresh_expiring_jwts)

# Register Flask JWT callbacks
jwt.token_in_blocklist_loader(check_if_token_revoked)
jwt.user_identity_loader(user_identity_lookup)
jwt.user_lookup_loader(user_lookup_callback)

# Compile Swagger JSON file
with app.app_context():
    swagger_data = api.__schema__
    with open(path.join(BASE_DIR, "../", "swagger.json"), "w", encoding="utf-8") as f:
        f.write(dumps(swagger_data))

if __name__ == "__main__":
    app.run()

from app import (backup, exceptions, jellyfin, mediarequest, notifications,
                 partials, plex, routes, scheduler, security, universal, web)
