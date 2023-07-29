from datetime import timedelta
from json import dumps
from os import environ, getenv, path, mkdir, access, W_OK, R_OK

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
from models.database import *
from api import *
from helpers.babel_locale import get_locale

# Global App Version
VERSION = "3.0.0"
BASE_DIR = path.abspath(path.dirname(__file__))

# Load environment variables
load_dotenv()

# Initialize the app and api
app = Flask(__name__)


# Stuff thats gonna prevent Wizarr from working correctly, lets tell the user about it instead of just quitting
@app.before_request
def before_request():
    if getenv("APP_URL") and getenv("APP_URL") != request.host or not getenv("APP_URL"):
        return render_template("error/custom.html", title="APP_URL", subtitle="APP_URL not configured correctly", description="It appears that APP_URL is not configured correctly in your Docker/System settings, APP_URL must match the URL your attempting to access this site on excluding http:// or https://"), 500

    database_path = path.abspath(path.join(BASE_DIR, "../", "database"))

    if not path.exists(database_path) or not path.isdir(database_path) or not access(database_path, W_OK) or not access(database_path, R_OK):
        return render_template("error/custom.html", title="DATABASE", subtitle="Database folder not writable", description="It appears that Wizarr does not have permissions over the database folder, please make sure that the folder is writable by the user running Wizarr."), 500

    sessions_path = path.abspath(path.join(BASE_DIR, "../", "database", "sessions"))

    if not path.exists(sessions_path) or not path.isdir(sessions_path) or not access(sessions_path, W_OK) or not access(sessions_path, R_OK):
        return render_template("error/custom.html", title="SESSIONS", subtitle="Sessions folder not writable", description="It appears that Wizarr does not have permissions over the sessions folder, please make sure that the folder is writable by the user running Wizarr."), 500

# Run database migrations scripts
migrate()

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
app.jinja_env.globals.update(GITHUB_SHEBANG="wizarrrr/wizarr")
app.jinja_env.globals.update(DOCS_URL="https://docs.wizarr.dev")
app.jinja_env.globals.update(DISCORD_INVITE="wsSTsHGsqu")
app.jinja_env.globals.update(APP_RELEASED="Beta" if is_beta() else "Stable")
app.jinja_env.globals.update(APP_LANG="en")
app.jinja_env.globals.update(TIMEZONE=getenv("TZ", "UTC"))
app.jinja_env.globals.update(DATA_DIRECTORY=path.abspath(path.join(BASE_DIR, "../", "database")))
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
app.config["DEBUG"] = True if getenv("DEBUG", "false") == "true" else False
app.config["CACHE_TYPE"] = "SimpleCache"
app.config["CACHE_DEFAULT_TIMEOUT"] = 300

sse = ServerSentEvents()

# Initialize App Extensions
sess.init_app(app)
htmx.init_app(app)
jwt.init_app(app)
cache.init_app(app)
api.init_app(app)
schedule.init_app(app)
babel.init_app(app, locale_selector=get_locale)

# Clear cache on startup
with app.app_context():
    cache.clear()

# Register Jinja2 filters
app.add_template_filter(format_datetime)
app.add_template_filter(date_format)
app.add_template_filter(env, "getenv")

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

from app import (backup, exceptions, mediarequest, notifications,
                 partials, plex, routes, scheduler, security)
