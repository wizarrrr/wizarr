import os
from datetime import datetime, timedelta

from dotenv import load_dotenv
from flask import Flask, request, session
from flask_babel import Babel
from flask_htmx import HTMX
from flask_session import Session
from flask_swagger_ui import get_swaggerui_blueprint
from peewee import *
from playhouse.migrate import *

from models import *

VERSION = "2.2.0"

app = Flask(__name__)
base_dir = os.path.abspath(os.path.dirname(__file__))

app.config["TEMPLATES_AUTO_RELOAD"] = True
app.config["SESSION_TYPE"] = "filesystem"
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY") or "secret_key"
app.config["SESSION_FILE_DIR"] = os.path.join(base_dir, "../", "database", "sessions")
app.config["LANGUAGES"] = {'en': 'english', 'de': 'german', 'zh': 'chinese', 'fr': 'french', 'sv': 'swedish', 'pt': 'portuguese', 'pt_BR': 'portuguese', 'lt': 'lithuanian', 'es': 'spanish', 'ca': 'catalan', 'pl': 'polish' }
app.config["BABEL_DEFAULT_LOCALE"] = "en"
app.config["BABEL_TRANSLATION_DIRECTORIES"] = ('./translations')
app.config["SCHEDULER_API_ENABLED"] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=5)

load_dotenv()

def get_locale():
    force_language = os.getenv("FORCE_LANGUAGE")
    lang = request.args.get('lang')
    
    session['lang'] = lang if lang else session.get('lang', None)
    return session.get('lang', 'en') if force_language is None else force_language

Session(app)
htmx = HTMX(app)
babel = Babel(app, locale_selector=get_locale)


# Swagger
swaggerui_blueprint = get_swaggerui_blueprint("/api-docs", "/api-docs/swagger.json")
app.register_blueprint(swaggerui_blueprint)

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
    

if __name__ == "__main__":
    app.run()

from app import (api, helpers, jellyfin, mediarequest, notifications, partials,
                 plex, routes, scheduler, tasks, universal, web)
