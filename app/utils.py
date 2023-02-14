from flask import current_app as app, request, session
import os


def get_locale():
     if os.getenv("FORCE_LANGUAGE"):
        return os.getenv("FORCE_LANGUAGE")
     elif request.args.get('lang'):
        session['lang'] = request.args.get('lang')
        return session.get('lang', 'en')
     else:
        return request.accept_languages.best_match(app.config['LANGUAGES'].keys())