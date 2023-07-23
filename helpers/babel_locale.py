from flask import request, session
from os import getenv
from logging import info

def get_locale():
    force_language = getenv("FORCE_LANGUAGE")
    session["lang"] = request.args.get("lang") or session.get("lang", None)
    local = session.get("lang", "en") if force_language is None else force_language

    info(f"App started with language {local}")

    return local
