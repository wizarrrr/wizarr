# app/error_handlers.py
from flask import render_template
import logging

def register_error_handlers(app):
    @app.errorhandler(500)
    def error_500(e):
        logging.error("500: %s", e, exc_info=True)
        return render_template("error/500.html"), 500

    @app.errorhandler(404)
    def error_404(e):
        logging.info("404: %s", e)
        return render_template("error/404.html"), 404

    @app.errorhandler(401)
    def error_401(e):
        logging.info("401: %s", e)
        return render_template("error/401.html"), 401
