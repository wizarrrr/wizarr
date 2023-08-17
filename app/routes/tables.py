from datetime import datetime
from os import getenv

from flask import Blueprint, render_template
from flask_jwt_extended import current_user
from app.security import login_required

tables = Blueprint("tables", __name__, template_folder="../views/tables/")

@tables.get("/partials/tables/<string:subpath>")
@login_required()
def table_partials(subpath):

    from app.models.database.accounts import Accounts
    from app.models.database.invitations import Invitations
    from app.models.database.mfa import MFA
    from app.models.database.oauth_clients import OAuthClients
    from app.models.database.sessions import Sessions
    from app.models.database.settings import Settings
    from app.scheduler import get_schedule
    from helpers import get_api_keys, get_notifications, get_users

    from api.routes.notifications_api import NotificationsListAPI

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
        data, _ = NotificationsListAPI().get(query="template")
        settings["notifications"] = data

    if subpath == "sessions-table":
        settings["sessions"] = Sessions.select().where(Sessions.user == current_user["id"]).order_by(Sessions.created.desc())

    if subpath == "api-table":
        settings["api_keys"] = get_api_keys()

    if subpath == "oauth-table":
        settings["oauth_clients"] = list(OAuthClients.select().dicts())

    if subpath == "mfa-table":
        settings["mfa_keys"] = list(MFA.select().where(MFA.user_id == current_user["id"]).dicts())

    return render_template(f"{subpath}.html", **settings)
