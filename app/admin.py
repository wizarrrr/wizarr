from flask import request, redirect, render_template
from app import app, Invitations, Settings, session, Users
from app.plex import *
from werkzeug.security import generate_password_hash, check_password_hash
from plexapi.server import PlexServer
import logging
from functools import wraps
import datetime
import random
import string
import os
from flask_babel import _


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if os.getenv("DISABLE_BUILTIN_AUTH"):
            if os.getenv("DISABLE_BUILTIN_AUTH") == "true":
                return f(*args, **kwargs)
        if not Settings.get_or_none(Settings.key == "admin_username"):
            return redirect('/settings')
        if not session.get("admin_key"):
            return redirect("/login")
        if session.get("admin_key") == Settings.get(Settings.key == "admin_key").value:
            return f(*args, **kwargs)
        else:
            return redirect("/login")

    return decorated_function


@app.route('/settings', methods=["GET", "POST"])
def preferences():
    if not Settings.select().where(Settings.key == 'admin_username').exists():

        if request.method == 'GET':
            return render_template("register_admin.html")

        elif request.method == 'POST':
            username = request.form.get("username")
            password = request.form.get("password")

            if password != request.form.get("confirm-password"):
                return render_template("register_admin.html", error=_("Passwords do not match."))

            if len(username) < 3 or len(username) > 15:
                return render_template("register_admin.html", error=_("Username must be between 3 and 15 characters."))

            if len(password) < 3 or len(password) > 40:
                return render_template("register_admin.html", error=_("Password must be between 3 and 40 characters."))
            hash = generate_password_hash(password, "sha256")
            Settings.create(key="admin_username", value=username)
            Settings.create(key="admin_password", value=hash)
            return redirect("/settings")

    elif Settings.select().where(Settings.key == 'admin_username').exists() and not Settings.select().where(Settings.key == "plex_verified", Settings.value == "True").exists():

        if request.method == 'GET':
            return render_template("verify_plex.html")

        elif request.method == 'POST':
            name = request.form.get("name")
            plex_url = request.form.get("plex_url")
            plex_token = request.form.get("plex_token")
            overseerr_url = None
            discord_id = None

            # Getting Libraries Properly
            libraries = []

            library_count = int(request.form.get("library_count"))
            for library in range(library_count+1):

                if request.form.get("plex_library_" + str(library)):
                    libraries.append(request.form.get(
                        "plex_library_" + str(library)))
            libraries = ', '.join(libraries)
            if not libraries:
                return render_template("settings.html", error=_("You must select at least one library."))

            if request.form.get("discord_id"):
                discord_id = request.form.get("discord_id")
            if request.form.get("overseerr_url"):
                overseerr_url = request.form.get("overseerr_url")

            Settings.create(key="plex_name", value=name)
            Settings.create(key="plex_url", value=plex_url)
            Settings.create(key="plex_token", value=plex_token)
            Settings.create(key="plex_libraries", value=libraries)
            if overseerr_url:
                Settings.create(key="overseerr_url", value=overseerr_url)
            if discord_id:
                Settings.create(key="discord_id", value=discord_id)
            Settings.create(key="plex_verified", value="True")
            return redirect("/")
    elif Settings.select().where(Settings.key == 'admin_username').exists() and Settings.select().where(Settings.key == "plex_verified", Settings.value == "True").exists():
        return redirect('/settings/')


@app.route('/settings/', methods=["GET", "POST"])
@login_required
def secure_settings():
    if request.method == 'GET':
        plex_name = Settings.get(Settings.key == "plex_name").value
        plex_url = Settings.get(Settings.key == "plex_url").value
        plex_libraries = Settings.get(Settings.key == "plex_libraries").value
        plex_token = Settings.get(Settings.key == "plex_token").value
        overseerr_url = Settings.get_or_none(
            Settings.key == "overseerr_url")
        discord_id = Settings.get_or_none(Settings.key == "discord_id")
        custom_html = Settings.get_or_none(Settings.key == "custom_html")
        if overseerr_url:
            overseerr_url = overseerr_url.value
        if discord_id:
            discord_id = discord_id.value
        if custom_html:
            custom_html = custom_html.value
        return render_template("settings.html", plex_name=plex_name, plex_url=plex_url, plex_libraries=plex_libraries, plex_token=plex_token, overseerr_url=overseerr_url, discord_id=discord_id, custom_html=custom_html)

    elif request.method == 'POST':
        name = request.form.get("name")
        plex_url = request.form.get("plex_url")
        plex_token = request.form.get("plex_token")
        discord_id = None
        overseerr_url = None
        custom_html = None

        # Getting Libraries Properly
        libraries = []
        library_count = int(request.form.get("library_count"))
        for library in range(library_count+1):

            if request.form.get("plex_library_" + str(library)):
                libraries.append(request.form.get(
                    "plex_library_" + str(library)))
        libraries = ', '.join(libraries)

        if not libraries:
            libraries = Settings.get(Settings.key == "plex_libraries").value

        if request.form.get("discord_id"):
            discord_id = request.form.get("discord_id")
        if request.form.get("overseerr_url"):
            overseerr_url = request.form.get("overseerr_url")
        if request.form.get("custom_html"):
            custom_html = request.form.get("custom_html")
        try:
            plex = PlexServer(plex_url, token=plex_token)
        except Exception as e:
            logging.error(str(e))
            if "unauthorized" in str(e):
                error = _("It is likely that your token does not work.")
            else:
                error = _(
                    "Unable to connect to your Plex server. See Logs for more information.")
            return render_template("verify_plex.html", error=error)
        Settings.update(value=name).where(
            Settings.key == "plex_name").execute()
        Settings.update(value=plex_url).where(
            Settings.key == "plex_url").execute()
        Settings.update(value=plex_token).where(
            Settings.key == "plex_token").execute()
        Settings.update(value=libraries).where(
            Settings.key == "plex_libraries").execute()
        if overseerr_url:
            Settings.delete().where(Settings.key == "overseerr_url").execute()
            Settings.create(key="overseerr_url", value=overseerr_url)
        if not overseerr_url:
            Settings.delete().where(Settings.key == "overseerr_url").execute()
        if discord_id:
            Settings.delete().where(Settings.key == "discord_id").execute()
            Settings.create(key="discord_id", value=discord_id)
        if not discord_id:
            Settings.delete().where(Settings.key == "discord_id").execute()
        if not custom_html:
            Settings.delete().where(Settings.key == "custom_html").execute()
        if custom_html:
            Settings.delete().where(Settings.key == "custom_html").execute()
            Settings.create(key="custom_html", value=custom_html)
        return redirect("/")


@app.route('/login', methods=["GET", "POST"])
def login():
    if request.method == 'GET':
        if os.getenv("DISABLE_BUILTIN_AUTH"):
            if os.getenv("DISABLE_BUILTIN_AUTH") == "true":
                return redirect("/")
        # Todo redirect to setup if not password
        return render_template("login.html")
    if request.method == 'POST':
        username = request.form.get("username")
        password = request.form.get("password")
        remember = request.form.get("remember")

        if Settings.get(Settings.key == "admin_username").value == username:
            if check_password_hash(Settings.get(Settings.key == "admin_password").value, password):

                key = ''.join(random.choices(
                    string.ascii_uppercase + string.digits, k=20))
                session["admin_key"] = key
                Settings.delete().where(Settings.key == "admin_key").execute()
                Settings.insert(key="admin_key", value=key).execute()
                if remember:
                    session.permanent = True
                else:
                    session.permanent = False
                logging.info(
                    "User successfully logged in the username " + username)
                return redirect("/")
            else:
                logging.warning(
                    "A user attempted to login with incorrect password for user: " + username)
                return render_template("login.html", error=_("Invalid Username or Password"))
        else:
            logging.warning(
                "A user attempted to login with incorrect username: " + username)
            return render_template("login.html", error=_("Invalid Username or Password"))


@app.route('/invites')
@login_required
def invites():
    return render_template("invites.html")


@app.route('/invite/table/delete=<delete_code>', methods=["POST"])
@login_required
def table(delete_code):
    if delete_code != "None":

        Invitations.delete().where(Invitations.code == delete_code).execute()
    invitations = Invitations.select().order_by(Invitations.created.desc())
    format = "%Y-%m-%d %H:%M"
    for invite in invitations:
        if invite.expires and datetime.datetime.strptime(invite.expires, format) <= datetime.datetime.now():
            invite.expired = True
        else:
            invite.expired = False
    return render_template("invite_table.html", invitations=invitations, rightnow=datetime.datetime.now())


@app.route('/users')
@login_required
def users():

    return render_template("users.html", users=users)


@app.route('/users/table')
@login_required
def users_table():

    if request.args.get("delete"):
        print("Deleting user " + request.args.get("delete"))
        try:
            deleteUser(request.args.get("delete"))
        except Exception as e:
            if "429" in str(e):
                logging.error("Too many requests to Plex API")
            else:
                logging.error("Unable to delete user: " + str(e))
    users = None
    try:
        users = getUsers()
        expiring = {}
        for user in users:
            expires = ExpiringInvitations.get_or_none(
                ExpiringInvitations.used_by == user.email)
            if expires:
                expires = expires.expires
            if expiring:
                expiring[user] = expires
            else:
                expiring[user] = None

    except Exception as e:
        if "429" in str(e):
            logging.error("Too many requests to Plex API")
        else:
            logging.error("Unable to get users: " + str(e))

    return render_template("user_table.html", users=users, expiring=expiring)
