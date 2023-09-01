from logging import getLogger

from flask import Blueprint, abort, render_template
from jinja2 import TemplateNotFound

logger = getLogger(__name__)

def page_not_found(e):
    logger.error("Page not found: %s", e)
    return render_template("errors/404.html"), 404

def internal_server_error(e):
    logger.error("Internal server errors: %s", e)
    return render_template("errors/500.html"), 500

def unauthorized(e):
    logger.error("Unauthorized: %s", e)
    return render_template("errors/401.html"), 401
