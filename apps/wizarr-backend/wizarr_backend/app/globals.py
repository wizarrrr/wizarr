from os import getenv, path
from flask import Flask
from app.utils.software_lifecycle import is_stable, need_update, get_current_version
from definitions import DATABASE_DIR

def create_globals(app: Flask):
    globals_config = {}
    globals_config["APP_NAME"] = "Wizarr"
    globals_config["APP_VERSION"] = get_current_version()
    globals_config["APP_GITHUB_URL"] = "https://github.com/Wizarrrr/wizarr"
    globals_config["GITHUB_SHEBANG"] = "wizarrrr/wizarr"
    globals_config["DOCS_URL"] = "https://docs.wizarr.dev"
    globals_config["DISCORD_INVITE"] = "wsSTsHGsqu"
    globals_config["APP_RELEASED"] = is_stable()
    globals_config["APP_LANG"] = "en"
    globals_config["TIMEZONE"] = getenv("TZ", "UTC")
    globals_config["DATA_DIRECTORY"] = DATABASE_DIR
    globals_config["APP_UPDATE"] = need_update()
    globals_config["DISABLE_BUILTIN_AUTH"] = bool(str(getenv("DISABLE_BUILTIN_AUTH", "False")).lower() == "true")
    globals_config["LANGUAGES"] = app.config["LANGUAGES"]

    return globals_config
