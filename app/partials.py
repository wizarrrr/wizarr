from datetime import datetime
from json import loads
from os import getenv, listdir, path

from flask import abort, render_template, request
from flask_jwt_extended import current_user

from app import app
from helpers import get_api_keys, get_notifications, get_settings, get_users

from models.database.accounts import Accounts
from models.database.invitations import Invitations
from models.database.oauth_clients import OAuthClients
from models.database.sessions import Sessions
from models.database.settings import Settings
from models.database.mfa import MFA

from .scheduler import get_schedule
from .security import login_required, login_required_unless_setup


# All admin partials
@app.get("/partials/admin", defaults={"subpath": ""})
@app.get("/partials/admin/<path:subpath>")
@login_required()
def admin_partials(subpath):
    # Get valid settings partials
    html_files = [path.splitext(file)[0] for file in listdir("./app/templates/admin") if file.endswith(".html")]

    # Check if the subpath is valid
    if subpath not in html_files and subpath != "":
        return abort(404)

    # Get all settings
    settings = get_settings()
    settings["admin"] = current_user

    # If no subpath is specified, render the admin dashboard
    if not subpath:
        return render_template("admin.html", subpath="admin/invite.html", **settings)

    # All possible admin partials
    return render_template(f"admin/{subpath}.html", **settings)



# All settings partials
@app.get("/partials/admin/settings", defaults={"subpath": ""})
@app.get("/partials/admin/settings/<path:subpath>")
@login_required()
def settings_partials(subpath):
    # Get valid settings partials
    html_files = [path.splitext(file)[0] for file in listdir("./app/templates/admin/settings") if file.endswith(".html")]

    # Check if the subpath is valid
    if subpath not in html_files and subpath != "":
        return abort(404)

    # Get all settings
    settings = get_settings()
    settings["admin"] = current_user

    # Import settings.json.j2 from root directory
    sections = app.jinja_env.get_template("settings.json.j2").render()
    sections = loads(sections)

    # If no subpath is specified, render the admin dashboard
    if not subpath:
        return render_template("admin/settings.html", settings_subpath="admin/settings/main.html", **settings, sections=sections)

    # All possible admin partials
    return render_template(f"admin/settings/{subpath}.html", **settings, sections=sections)



# All modal partials
@app.get("/partials/modals/<string:subpath>")
@login_required_unless_setup()
def modal_partials(subpath, **kwargs):
    # Get all form and post data
    form = request.form if request.form else {}
    post = request.args if request.args else {}
    args = kwargs if kwargs else {}

    # Merge form and post data
    data = {**form, **post, **args}

    return render_template("modal.html", subpath=f"modals/{subpath}.html", **data)


# All tables partials
@app.get("/partials/tables/<string:subpath>")
@login_required()
def table_partials(subpath):
    settings = {
        "admin": current_user
    }

    if subpath == "global-users":
        settings["users"] = get_users(as_dict=True)

    if subpath == "invite-table":
        settings["server_type"] = Settings.get(key="server_type").value
        settings["invitations"] = Invitations.select().order_by(Invitations.created.desc())
        settings["rightnow"] = datetime.now()
        settings["app_url"] = getenv("APP_URL")

    if subpath == "admin-users":
        settings["admins"] = list(Accounts.select().dicts())

    if subpath == "task-table":
        settings["tasks"] = get_schedule()

    if subpath == "notification-table":
        settings["notifications"] = get_notifications()

    if subpath == "sessions-table":
        settings["sessions"] = Sessions.select().where(Sessions.user == current_user["id"]).order_by(Sessions.created.desc())

    if subpath == "api-table":
        settings["api_keys"] = get_api_keys()

    if subpath == "oauth-table":
        settings["oauth_clients"] = list(OAuthClients.select().dicts())

    if subpath == "mfa-table":
        settings["mfa_keys"] = list(MFA.select().where(MFA.user_id == current_user["id"]).dicts())

    return render_template(f"tables/{subpath}.html", **settings)
