import asyncio
import queue
from logging import error, webpush
from os import getenv, listdir, path
from threading import Thread

from flask import (Response, abort, redirect, render_template,
                   send_from_directory)
from flask_jwt_extended import current_user, jwt_required
from playhouse.shortcuts import model_to_dict

from app import VERSION, app
from app.helpers import get_api_keys, get_settings, is_invite_valid
from app.security import logged_out_required, login_required
from models.settings import Settings


# Static files
@app.route('/favicon.ico')
def favicon():
    return send_from_directory(path.join(app.root_path, 'static'), 'favicon.ico', mimetype='image/vnd.microsoft.icon')

# All admin routes
@app.get('/admin', defaults={'subpath': ''})
@app.get('/admin/<path:subpath>')
@login_required()
def admin_routes(subpath):
    # Get valid settings partials
    html_files = [path.splitext(file)[0] for file in listdir(
        './app/templates/admin') if file.endswith('.html')]

    # Check if the subpath is valid
    if subpath not in html_files and subpath != "":
        return abort(404)
    
    # Authentication Activated
    settings = get_settings()
    settings["auth"] = True if getenv("DISABLE_BUILTIN_AUTH") != "true" else False

    # If no subpath is specified, render the admin dashboard
    if not subpath:
        return render_template("admin.html", subpath="admin/invite.html", **settings)

    # All possible admin routes
    return render_template("admin.html", subpath=f"admin/{subpath}.html", **settings)


# All settings routes
@app.get('/admin/settings', defaults={'subpath': ''})
@app.get('/admin/settings/<path:subpath>')
@login_required()
def settings_routes(subpath):
    # Get valid settings partials
    html_files = [path.splitext(file)[0] for file in listdir(
        './app/templates/admin/settings') if file.endswith('.html')]

    # Check if the subpath is valid
    if subpath not in html_files and subpath != "":
        return abort(404)

    # Get all settings
    settings = get_settings()
    settings["api_keys"] = get_api_keys()
    settings["template"] = subpath if subpath else "general"
    settings["auth"] = True if getenv("DISABLE_BUILTIN_AUTH") != "true" else False
    settings["admin"] = current_user

    # If no subpath is specified, render the admin dashboard
    if not subpath:
        return render_template("admin.html", subpath="admin/settings.html", settings_subpath="admin/settings/general.html", **settings)

    # All possible admin routes
    return render_template("admin.html", subpath="admin/settings.html", settings_subpath=f"admin/settings/{subpath}.html", **settings)

# All account routes
@app.get('/admin/account', defaults={'subpath': ''})
@app.get('/admin/account/<path:subpath>')
@login_required()
def account_routes(subpath):
    # Get valid account partials
    html_files = [path.splitext(file)[0] for file in listdir('./app/templates/admin/account') if file.endswith('.html')]

    # Check if the subpath is valid
    if subpath not in html_files and subpath != "":
        return abort(404)

    # Get all settings
    settings = get_settings()
    settings["template"] = subpath if subpath else "general"
    settings["admin"] = current_user

    # If no subpath is specified, render the admin dashboard
    if not subpath:
        return render_template("admin.html", subpath="admin/account.html", account_subpath="admin/account/general.html", **settings)

    # All possible admin partials
    return render_template("admin.html", subpath="admin/account.html", account_subpath=f"admin/account/{subpath}.html", **settings)


# All setup routes
@app.route('/setup/<path:subpath>', methods=["GET"])
def setup_routes(subpath):
    # Get all settings
    settings = get_settings()

    # If the server is already verified, redirect to the admin dashboard
    # if "server_verified" in settings and settings["server_verified"]:
        # return redirect("/")

    html_files = [path.splitext(file)[0] for file in listdir('./app/templates/setup/pages') if file.endswith('.html')]

    if subpath not in html_files:
        return abort(404)

    # I could of used html_files however I wanted to keep the order of the pages
    pages = [
        'welcome',
        'database',
        'admin',
        'settings',
        'complete'
    ]

    data = {
        "partials": [f"setup/pages/{page}.html" for page in pages],
        "current": (pages.index(subpath)) + 1,
        "pages": pages
    }

    data.update(settings)

    return render_template("setup/base.html", **data)


# Invite route
@app.route("/j/<code>", methods=["GET"])
def invite_route(code):
    
    valid, message = is_invite_valid(code)
    server_type = Settings.get(key="server_type").value

    if not valid:
        return render_template('invite/invite-invalid.html', error=message)
    
    return render_template("invite/signup.html", partial=f"invite/signup/{server_type}.html", code=code)
    
# Login route
@app.route('/login', methods=["GET"])
@logged_out_required()
def login_get():
    if getenv("DISABLE_BUILTIN_AUTH") and getenv("DISABLE_BUILTIN_AUTH") == "true":
        return redirect("/")

    return render_template("login.html")



# Handle 404, 401 and 500 errors
def error_handler(code):
    @app.errorhandler(code)
    def handler(exception):
        error(exception)
        return render_template(f'error/{code}.html'), code

for code in [500, 404, 401]:
    error_handler(code)