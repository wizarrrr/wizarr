from datetime import timedelta
from os import environ, getenv, path

from flask import Flask

from app.utils.get_languages import get_languages
from app.security import secret_key

def create_config(app: Flask):
    config = {}
    base_dir = path.abspath(path.join(path.dirname(__file__), "../"))

    config["TEMPLATES_AUTO_RELOAD"] = True
    config["SESSION_TYPE"] = "filesystem"
    config["SESSION_FILE_DIR"] = path.join(base_dir, "database", "sessions")
    config["LANGUAGES"] = get_languages()
    config["BABEL_DEFAULT_LOCALE"] = "en"
    config["BABEL_TRANSLATION_DIRECTORIES"] = path.join(base_dir, "app", "translations")
    config["SCHEDULER_API_ENABLED"] = True
    config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=5)
    config["UPLOAD_FOLDER"] = path.join(base_dir, "database", "uploads")
    config["SWAGGER_UI_DOC_EXPANSION"] = "list"
    config["SERVER_NAME"] = getenv("APP_URL")
    config["APPLICATION_ROOT"] = "/"
    config["PREFERRED_URL_SCHEME"] = "https" if getenv("HTTPS", "false") == "true" else "http"
    config["JWT_SECRET_KEY"] = secret_key()
    config["JWT_BLACKLIST_ENABLED"] = True
    config["JWT_TOKEN_LOCATION"] = ["headers", "cookies", "json", "query_string"]
    config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=1)
    config["JWT_COOKIE_CSRF_PROTECT"] = True
    config["JWT_COOKIE_SECURE"] = not app.debug
    config["DEBUG"] = app.debug
    config["CACHE_TYPE"] = "SimpleCache"
    config["CACHE_DEFAULT_TIMEOUT"] = 300
    config["PROPAGATE_EXCEPTIONS"] = app.debug
    config["GUNICORN"] = "gunicorn" in environ.get("SERVER_SOFTWARE", "")

    return config
