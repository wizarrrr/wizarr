from datetime import datetime
from os import getenv, listdir, path

from flask import abort, make_response, render_template, request

from app import app, session
from models import Admins, Invitations, Sessions, Settings

from .helpers import (get_api_keys, get_notifications, get_settings,
                      login_required)
from .scheduler import get_schedule
from .universal import global_get_users


# All admin partials
@app.get('/partials/admin', defaults={'subpath': ''})
@app.get('/partials/admin/<path:subpath>')
@login_required
def admin_partials(subpath):
    # Get valid settings partials
    html_files = [path.splitext(file)[0] for file in listdir('./app/templates/admin') if file.endswith('.html')]

    # Check if the subpath is valid
    if subpath not in html_files and subpath != "":
        return abort(404)

    # If no subpath is specified, render the admin dashboard
    if not subpath:
        return render_template("admin.html", subpath="admin/invite.html")

    # All possible admin partials
    return render_template(f"admin/{subpath}.html")



# All settings partials
@app.get('/partials/admin/settings', defaults={'subpath': ''})
@app.get('/partials/admin/settings/<path:subpath>')
@login_required
def settings_partials(subpath):
    # Get valid settings partials
    html_files = [path.splitext(file)[0] for file in listdir('./app/templates/admin/settings') if file.endswith('.html')]

    # Check if the subpath is valid
    if subpath not in html_files and subpath != "":
        return abort(404)

    # Get all settings
    settings = get_settings()
    settings["api_keys"] = get_api_keys()
    settings["template"] = subpath if subpath else "general"
    settings["admin"] = session["admin"]

    # If no subpath is specified, render the admin dashboard
    if not subpath:
        return render_template("admin/settings.html", settings_subpath="admin/settings/general.html", **settings)

    # All possible admin partials
    return render_template(f"admin/settings/{subpath}.html", **settings)

@app.post('/partials/admin/settings', defaults={'subpath': ''})
@app.post('/partials/admin/settings/<path:subpath>')
@login_required
def post_settings_routes(subpath):
    # Get valid settings partials
    # if subpath in ["general", "request", "discord", "html"]:
    # SettingsController(request).post()
        
    response = make_response(settings_partials(subpath))
    response.headers['showToast'] = "Settings saved successfully!"
    
    return response

# All account partials
@app.get('/partials/admin/account', defaults={'subpath': ''})
@app.get('/partials/admin/account/<path:subpath>')
@login_required
def account_partials(subpath):
    # Get valid account partials
    html_files = [path.splitext(file)[0] for file in listdir('./app/templates/admin/account') if file.endswith('.html')]

    # Check if the subpath is valid
    if subpath not in html_files and subpath != "":
        return abort(404)

    # Get all settings
    settings = get_settings()
    settings["template"] = subpath if subpath else "general"
    settings["admin"] = session["admin"]

    # If no subpath is specified, render the admin dashboard
    if not subpath:
        return render_template("admin/account.html", account_subpath="admin/account/general.html", **settings)

    # All possible admin partials
    return render_template(f"admin/account/{subpath}.html", **settings)


# All modal partials
@app.route('/partials/modals/<path:path>')
@login_required
def modal_partials(path, **kwargs):
    # Get all form and post data
    form = request.form if request.form else {}
    post = request.args if request.args else {}
    args = kwargs if kwargs else {}

    # Merge form and post data
    data = {**form, **post, **args}

    return render_template("modal.html", subpath=f"modals/{path}.html", **data)



# All tables partials
@app.route('/partials/tables/<path:path>')
@login_required
def table_partials(path):
    settings = {
        "admin": session["admin"]
    }

    if path == "global-users":
        settings["users"] = global_get_users()

    if path == "invite-table":
        settings["server_type"] = Settings.get(key="server_type").value
        settings["invitations"] = Invitations.select().order_by(Invitations.created.desc())
        settings["rightnow"] = datetime.now()
        settings["app_url"] = getenv("APP_URL")
        
    if path == "admin-users":
        settings["admins"] = list(Admins.select().dicts())
        
    if path == "task-table":
        settings["tasks"] = get_schedule()
        
    if path == "notification-table":
        settings["notifications"] = get_notifications()
        
    if path == "sessions-table":
        settings["sessions"] = Sessions.select().where(Sessions.user == session["admin"]["id"]).order_by(Sessions.created.desc())
        
    if path == "api-table":
        settings["api_keys"] = get_api_keys()

    return render_template(f"tables/{path}.html", **settings)