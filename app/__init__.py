import os

from dotenv import load_dotenv
from flask import Flask, request, session
from flask_apscheduler import APScheduler
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
app.config["SESSION_FILE_DIR"] = "./database/sessions"
app.config["LANGUAGES"] = {'en': 'english', 'de': 'german', 'zh': 'chinese', 'fr': 'french', 'sv': 'swedish', 'pt': 'portuguese', 'pt_BR': 'portuguese', 'lt': 'lithuanian', 'es': 'spanish', 'ca': 'catalan', 'pl': 'polish' }
app.config["BABEL_DEFAULT_LOCALE"] = "en"
app.config["BABEL_TRANSLATION_DIRECTORIES"] = ('./translations')
app.config["SCHEDULER_API_ENABLED"] = True

load_dotenv()

def get_locale():
    if os.getenv("FORCE_LANGUAGE"):
        return os.getenv("FORCE_LANGUAGE")
    elif request.args.get('lang'):
        session['lang'] = request.args.get('lang')
        return session.get('lang', 'en')
    
    return request.accept_languages.best_match(app.config['LANGUAGES'].keys())

Session(app)
htmx = HTMX(app)
babel = Babel(app, locale_selector=get_locale)

# Scheduler
scheduler = APScheduler()
scheduler.init_app(app)
scheduler.start()

# Swagger
swaggerui_blueprint = get_swaggerui_blueprint("/api-docs", "/api-docs/swagger.json")
app.register_blueprint(swaggerui_blueprint)

if __name__ == "__main__":
    app.run()

from app import (api, helpers, jellyfin, mediarequest, notifications, partials,
                 plex, routes, tasks, universal, web)
