from flask_babel import Babel
from flask_session import Session
from flask_apscheduler import APScheduler
from flask_htmx import HTMX
from flask_login import LoginManager, UserMixin
from flask_sqlalchemy import SQLAlchemy
from flask import request, session, current_app
from flask_migrate import Migrate

# Instantiate extensions
db = SQLAlchemy()
babel = Babel()
sess = Session()
scheduler = APScheduler()
htmx = HTMX()
login_manager = LoginManager()
migrate = Migrate()

# Initialize with app
def init_extensions(app):
    sess.init_app(app)
    babel.init_app(app, locale_selector=_select_locale)
    #scheduler.init_app(app)
    #scheduler.start()
    htmx.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    db.init_app(app)
    migrate.init_app(app, db)
    

@login_manager.user_loader
def load_user(user_id):
    from .models import AdminUser

    if user_id == "admin":
        return AdminUser()
    # no DB-backed users for now
    return None

def _select_locale():
    if (forced := current_app.config.get("FORCE_LANGUAGE")):
        return forced
    if (arg := request.args.get("lang")):
        session["lang"] = arg
        return arg
    return session.get(
        "lang",
        request.accept_languages.best_match(current_app.config["LANGUAGES"].keys()),
    )
