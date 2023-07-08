from datetime import datetime
from os import getenv, listdir, path

from flask import abort, make_response, render_template, request

from app import Invitations, Settings, app, controllers
from app.helpers import get_api_keys, get_notifications, get_settings
from app.universal import global_get_users


# All admin partials
@app.get('/partials/admin', defaults={'subpath': ''})
@app.get('/partials/admin/<path:subpath>')
# @login_required
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
# @login_required
def settings_partials(subpath):
    # Get valid settings partials
    html_files = [path.splitext(file)[0] for file in listdir('./app/templates/admin/settings') if file.endswith('.html')]

    # Check if the subpath is valid
    if subpath not in html_files and subpath != "":
        return abort(404)

    # Get all settings
    settings = get_settings()
    settings["agents"] = get_notifications()
    settings["api_keys"] = get_api_keys()
    settings["template"] = subpath if subpath else "general"

    # If no subpath is specified, render the admin dashboard
    if not subpath:
        return render_template("admin/settings.html", settings_subpath="admin/settings/general.html", **settings)

    # All possible admin partials
    return render_template(f"admin/settings/{subpath}.html", **settings)

@app.post('/partials/admin/settings', defaults={'subpath': ''})
@app.post('/partials/admin/settings/<path:subpath>')
def post_settings_routes(subpath):
    # Get valid settings partials
    if subpath in ["general", "request", "discord", "html"]:
        controllers.post_settings(request.form)
        
    response = make_response(settings_partials(subpath))
    response.headers['showToast'] = "Settings saved successfully!"
    
    return response

# All modal partials
@app.route('/partials/modals/<path:path>')
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
def table_partials(path):
    data = {}

    if path == "global-users":
        data = {
            "users": global_get_users()
        }

    if path == "invite-table":
        data = {
            "server_type": Settings.get(key="server_type").value,
            "invitations": Invitations.select().order_by(Invitations.created.desc()),
            "rightnow": datetime.now(),
            "app_url": getenv("APP_URL")
        }

    return render_template(f"tables/{path}.html", **data)