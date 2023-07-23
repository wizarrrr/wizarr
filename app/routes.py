from logging import error
from os import getenv, listdir, path

from flask import (abort, redirect, render_template,
                   send_from_directory)
from flask_jwt_extended import current_user

from app import app
from app.security import (logged_out_required, login_required,
                          server_not_verified_required,
                          server_verified_required)
from helpers import get_api_keys, get_setting, get_settings, is_invite_valid
from models.settings import Settings


@app.context_processor
def inject_user():
    return { "server_name": get_setting("server_name", "Wizarr") }

# Static files
@app.get('/favicon.ico')
def favicon():
    return send_from_directory(path.join(app.root_path, 'static'), 'favicon.ico', mimetype='image/vnd.microsoft.icon')

# All public facing routes
@app.get('/')
@server_verified_required()
def homepage_route():
    return render_template("homepage.html")

@app.get('/join')
@server_verified_required()
def join_route():
    return render_template("invite/join.html")


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
    settings["auth"] = True if getenv("DISABLE_BUILTIN_AUTH", "false") == "true" else False

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
    settings["auth"] = True if getenv("DISABLE_BUILTIN_AUTH", "false") == "true" else False
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
    settings["admin"] = current_user

    # If no subpath is specified, render the admin dashboard
    if not subpath:
        return render_template("admin.html", subpath="admin/account.html", account_subpath="admin/account/general.html", **settings)

    # All possible admin partials
    return render_template("admin.html", subpath="admin/account.html", account_subpath=f"admin/account/{subpath}.html", **settings)


# All setup routes
@app.get('/setup', defaults={'subpath': 'welcome'})
@app.get('/setup/', defaults={'subpath': 'welcome'})
@app.get('/setup/<path:subpath>')
@server_not_verified_required()
def setup_routes(subpath):
    # Get all settings
    settings = get_settings()

    print(settings)

    html_files = [path.splitext(file)[0] for file in listdir('./app/templates/setup/pages') if file.endswith('.html')]

    if subpath not in html_files:
        return abort(404)

    # I could of used html_files list however I wanted to keep the order of the pages instead of alphabetical order
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


# All help routes
@app.get('/help', defaults={'subpath': 'welcome'})
@app.get('/help/<path:subpath>')
def help_routes(subpath):
    from app import get_locale

    # Get all settings
    settings = get_settings()
    server_type = settings["server_type"]

    pages = [
        {
            "name": "welcome",
            "template": f"wizard/pages/{server_type}/welcome.html"
        },
        {
            "name": "download",
            "template": f"wizard/pages/{server_type}/download.html"
        },
        {
            "name": "requests",
            "template": "wizard/pages/requests.html",
            "enabled": bool(settings.get("request_type") != 'None')
        },
        {
            "name": "discord",
            "template": "wizard/pages/" + ("discord-widget.html" if not settings.get("discord_widget") else "discord.html"),
            "enabled": bool(settings.get("discord_id"))
        },
        {
            "name": "custom",
            "template": "wizard/pages/custom.html",
            "enabled": settings.get("custom_html")
        },
        {
            "name": "tips",
            "template": f"wizard/pages/{server_type}/tips.html"
        }
    ]
    print(bool(settings.get("discord_id")))

    partials = [page["template"] for page in pages if page.get("enabled", True)]
    current = [page["name"] for page in pages if page.get("enabled", True)].index(subpath)


    data = {
        "partials": partials,
        "current": current,
        "server_type": server_type,
        "server_url": settings.get("server_url"),
    }

    data.update(settings)

    return render_template("wizard/base.html", **data)


# Invite route
@app.get("/j/<code>")
@server_verified_required()
def invite_route(code):

    valid, message = is_invite_valid(code)
    server_type = Settings.get(key="server_type").value

    if not valid:
        return render_template('invite/invite-invalid.html', error=message)

    return render_template("invite/signup.html", partial=f"invite/signup/{server_type}.html", code=code)

# Login route
@app.get('/login')
@logged_out_required()
def login_get():
    if getenv("DISABLE_BUILTIN_AUTH", "false") == "true":
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