from flask import request, session
from os import getenv

def get_locale():
    force_language = getenv("FORCE_LANGUAGE")
    session["lang"] = request.args.get("lang") or session.get("lang", None)
    local = session.get("lang", "en") if force_language is None else force_language

    if local is None:
        local = request.accept_languages.best_match(["en", "de"])
        session["lang"] = local

    return local
