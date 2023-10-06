from datetime import timedelta
from os import environ, getenv, path

from flask import Flask

from app.security import secret_key, SchedulerAuth

def create_config(app: Flask):
    config = {}
    base_dir = path.abspath(path.join(path.dirname(__file__), "../"))

    config["SESSION_TYPE"] = "filesystem"
    config["SESSION_FILE_DIR"] = path.join(base_dir, "../", "database", "sessions")
    config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=5)
    config["UPLOAD_FOLDER"] = path.join(base_dir, "../", "database", "uploads")
    config["SWAGGER_UI_DOC_EXPANSION"] = "list"
    config["SERVER_NAME"] = "127.0.0.1:5000"
    config["APPLICATION_ROOT"] = "/"
    config["JWT_SECRET_KEY"] = secret_key()
    config["JWT_BLACKLIST_ENABLED"] = True
    config["JWT_TOKEN_LOCATION"] = ["headers", "json", "query_string"]
    config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=1)
    config["JWT_REFRESH_TOKEN_EXPIRES"] = timedelta(days=31)
    config["JWT_COOKIE_CSRF_PROTECT"] = True
    config["JWT_COOKIE_SECURE"] = False
    config["DEBUG"] = app.debug
    config["CACHE_TYPE"] = "SimpleCache"
    config["CACHE_DEFAULT_TIMEOUT"] = 300
    config["PROPAGATE_EXCEPTIONS"] = app.debug
    config["GUNICORN"] = "gunicorn" in environ.get("SERVER_SOFTWARE", "")
    config['JSONIFY_PRETTYPRINT_REGULAR'] = True
    config["SCHEDULER_TIMEZONE"] = "Europe/London"
    config["SCHEDULER_API_ENABLED"] = True
    config["SCHEDULER_API_PREFIX"] = "/api/scheduler"
    config["SCHEDULER_AUTH"] = SchedulerAuth()

    return config
