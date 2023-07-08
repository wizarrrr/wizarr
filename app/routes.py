from json import loads
from os import getenv, listdir, path

from flask import abort, redirect, render_template, request, session

from app import VERSION, app
from app.helpers import (get_api_keys, get_notifications, get_settings,
                         login_required)


# All admin routes
@app.get('/admin', defaults={'subpath': ''})
@app.get('/admin/<path:subpath>')
@login_required
def admin_routes(subpath):
    # Get valid settings partials
    html_files = [path.splitext(file)[0] for file in listdir(
        './app/templates/admin') if file.endswith('.html')]

    # Check if the subpath is valid
    if subpath not in html_files and subpath != "":
        return abort(404)

    # If no subpath is specified, render the admin dashboard
    if not subpath:
        return render_template("admin.html", subpath="admin/invite.html")

    # All possible admin routes
    return render_template("admin.html", subpath=f"admin/{subpath}.html")


# All settings routes
@app.get('/admin/settings', defaults={'subpath': ''})
@app.get('/admin/settings/<path:subpath>')
@login_required
def settings_routes(subpath):
    # Get valid settings partials
    html_files = [path.splitext(file)[0] for file in listdir(
        './app/templates/admin/settings') if file.endswith('.html')]

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
        return render_template("admin.html", subpath="admin/settings.html", settings_subpath="admin/settings/general.html", **settings)

    # All possible admin routes
    return render_template("admin.html", subpath="admin/settings.html", settings_subpath=f"admin/settings/{subpath}.html", **settings)


@app.route('/setup/<path:subpath>', methods=["GET"])
def setup_server(subpath):
    # Get all settings
    settings = get_settings()

    # If the server is already verified, redirect to the admin dashboard
    if "server_verified" in settings and settings["server_verified"]:
        return redirect("/")

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


# Login route


@app.route('/login', methods=["GET"])
def login_get():
    if getenv("DISABLE_BUILTIN_AUTH") and getenv("DISABLE_BUILTIN_AUTH") == "true":
        return redirect("/")
    
    if session.get("admin_key"):
        return redirect("/")

    return render_template("login.html")

@app.route("/api-docs/swagger.json")
def swaggerjson():
    swag = loads((open("./swagger.json", "r").read()))
    swag['info']['version'] = VERSION
    return swag
