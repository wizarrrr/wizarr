from logging import getLogger

from flask import Blueprint, abort, render_template
from jinja2 import TemplateNotFound

from app.security import server_verified_required
from helpers import is_invite_valid
from models.database.settings import Settings

invite = Blueprint("invite", __name__, template_folder="../views/client/invite/")
logger = getLogger(__name__)

@invite.route("/join")
@server_verified_required()
def join_route():
    return render_template("join.html")


@invite.route("/j/<string:code>")
@server_verified_required()
def invite_route(code):
    # Check if invite code is valid, and get the server type
    valid, message = is_invite_valid(code)
    server_type = Settings.get(key="server_type").value

    # If the invite code is not valid, return the invalid invite page
    if not valid:
        logger.error("Invalid invite code: %s", message)
        return render_template("invite-invalid.html", error=message)

    # If the invite code is valid, return the invite page
    return render_template("signup.html", partial=f"signup/{server_type}.html", code=code)
