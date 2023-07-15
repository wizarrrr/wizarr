import os
from datetime import datetime, timedelta, timezone
from logging import info, warning
from os import getenv

from dotenv import load_dotenv
from flask import Flask, request, send_file, session
from flask_babel import Babel
from flask_htmx import HTMX
from flask_jwt_extended import (JWTManager, create_access_token, current_user,
                                get_jti, get_jwt, get_jwt_identity,
                                jwt_required, set_access_cookies)
from flask_session import Session
from packaging import version
from peewee import *
from playhouse.migrate import *
from playhouse.shortcuts import model_to_dict
from requests import get

from api import *
from app.security import secret_key
from models import *

VERSION = "2.2.0"

app = Flask(__name__)
base_dir = os.path.abspath(os.path.dirname(__file__))
api.init_app(app)

os.environ["VERSION"] = VERSION

def need_update():
    try:
        r = get(url="https://raw.githubusercontent.com/Wizarrrr/wizarr/master/.github/latest")
        data = r.content.decode("utf-8")
        return version.parse(VERSION) < version.parse(data)
    except Exception as e:
        warning(f"Error checking for updates: {e}")
        return False

app.jinja_env.globals.update(APP_NAME="Wizarr")
app.jinja_env.globals.update(APP_VERSION=VERSION)
app.jinja_env.globals.update(APP_GITHUB_URL="https://github.com/Wizarrrr/wizarr")
app.jinja_env.globals.update(APP_RELEASED="Released")
app.jinja_env.globals.update(APP_LANG="en")
app.jinja_env.globals.update(APP_UPDATE=need_update())
app.jinja_env.globals.update(DISABLE_BUILTIN_AUTH=getenv("DISABLE_BUILTIN_AUTH", False))

app.config["TEMPLATES_AUTO_RELOAD"] = True
app.config["SESSION_TYPE"] = "filesystem"
app.config["SESSION_FILE_DIR"] = os.path.join(base_dir, "../", "database", "sessions")
app.config["LANGUAGES"] = {'en': 'english', 'de': 'german', 'zh': 'chinese', 'fr': 'french', 'sv': 'swedish', 'pt': 'portuguese', 'pt_BR': 'portuguese', 'lt': 'lithuanian', 'es': 'spanish', 'ca': 'catalan', 'pl': 'polish' }
app.config["BABEL_DEFAULT_LOCALE"] = "en"
app.config["BABEL_TRANSLATION_DIRECTORIES"] = ('./translations')
app.config["SCHEDULER_API_ENABLED"] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=5)
app.config['UPLOAD_FOLDER'] = os.path.join(base_dir, "../", "database", "uploads")
app.config['SWAGGER_UI_DOC_EXPANSION'] = 'list'
app.config['SERVER_NAME'] = getenv("APP_URL")
app.config['APPLICATION_ROOT'] = '/'
app.config['PREFERRED_URL_SCHEME'] = 'http'
app.config["JWT_SECRET_KEY"] = secret_key()
app.config["JWT_BLACKLIST_ENABLED"] = True
app.config["JWT_TOKEN_LOCATION"] = ["headers", "cookies", "json", "query_string"]
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=1)
app.config["JWT_COOKIE_CSRF_PROTECT"] = True
app.config["JWT_COOKIE_SECURE"] = True if app.debug is False else False

load_dotenv()

def get_locale():
    force_language = os.getenv("FORCE_LANGUAGE")
    lang = request.args.get('lang')
    
    session['lang'] = lang if lang else session.get('lang', None)
    return session.get('lang', 'en') if force_language is None else force_language

sess = Session(app)
htmx = HTMX(app)
babel = Babel(app, locale_selector=get_locale)
jwt = JWTManager(app)

@app.template_filter()
def format_datetime(value):
    format_str = '%Y-%m-%d %H:%M:%S.%f%z'

    def get_time_duration(target_date):
        now = datetime.now(target_date.tzinfo)
        duration = target_date - now
        duration_seconds = duration.total_seconds()

        hours = int(duration_seconds / 3600)
        minutes = int((duration_seconds % 3600) / 60)
        seconds = int(duration_seconds % 60)

        return hours, minutes, seconds

    parsed_date = datetime.strptime(value, format_str)
    hms = get_time_duration(parsed_date)
    
    if hms[0] > 0:
        return f"{hms[0]}h {hms[1]}m {hms[2]}s"
    elif hms[1] > 0:
        return f"{hms[1]}m {hms[2]}s"
    else:
        return f"{hms[2]}s"

@app.after_request
def refresh_expiring_jwts(response):
    try:
        jwt = get_jwt()
        exp_timestamp, jti = jwt["exp"], jwt["jti"]
        target_timestamp = datetime.timestamp(datetime.now(timezone.utc) + timedelta(minutes=30))
        if target_timestamp > exp_timestamp:
            access_token = create_access_token(identity=get_jwt_identity())
            Sessions.update(session=get_jti(access_token)).where(Sessions.session == jti).execute()
            set_access_cookies(response, access_token)
            info(f"Refreshed JWT for {get_jwt_identity()}")
        return response
    except (RuntimeError, KeyError):
        # Case where there is not a valid JWT. Just return the original response
        return response
    
@jwt.token_in_blocklist_loader
def check_if_token_revoked(jwt_header, jwt_payload: dict) -> bool:
    jti = jwt_payload["jti"]
    token = Sessions.get_or_none(Sessions.session == jti)

    return token is None

@jwt.user_identity_loader
def _user_identity_lookup(user):
    return user

@jwt.user_lookup_loader
def _user_lookup_callback(_jwt_header, jwt_data):
    identity = jwt_data["sub"]
    user = Admins.get_by_id(identity)
    return model_to_dict(user, recurse=True, backrefs=True, exclude=[Admins.password])


@app.template_filter()
def date_format(value, format="%Y-%m-%d %H:%M:%S"):
    format_str = '%Y-%m-%d %H:%M:%S'
    parsed_date = datetime.strptime(str(value), format_str)
    return parsed_date.strftime(format)

with app.app_context():
    swagger_data = api.__schema__
    with open(os.path.join(base_dir, "swagger.json"), "w") as f:
        f.write(dumps(swagger_data))

if __name__ == "__main__":
    sess.init_app(app)
    app.run()

from app import (backup, exceptions, helpers, jellyfin, mediarequest,
                 notifications, partials, plex, routes, scheduler, security,
                 tasks, universal, web)
