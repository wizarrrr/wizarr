from flask import request, redirect, render_template
from app import app, Invitations, Settings, session, Users
from app.plex import *
import secrets
from app.jellyfin import *
from app.helpers import *
from werkzeug.security import generate_password_hash, check_password_hash
from plexapi.server import PlexServer
import logging
from functools import wraps
import datetime
from packaging import version
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


@app.route('/admin')
@login_required
def admin():
    return render_template("admin.html")


@app.route('/invite', methods=["GET", "POST"])
@login_required
def invite():
    update_msg = False
    if request.method == "POST":
        try:
            code = request.form.get("code").upper()
            if not len(code) == 6:
                return abort(401)
        except:
            code = ''.join(secrets.choice(
                string.ascii_uppercase + string.digits) for _ in range(6))
        if Invitations.get_or_none(code=code):
            return abort(401)  # Already Exists
        expires = None
        unlimited = 0
        duration = None
        specific_libraries = None
        if request.form.get("expires") == "day":
            expires = (datetime.datetime.now() +
                       datetime.timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
        if request.form.get("expires") == "week":
            expires = (datetime.datetime.now() +
                       datetime.timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
        if request.form.get("expires") == "month":
            expires = (datetime.datetime.now() +
                       datetime.timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
        if request.form.get("expires") == "never":
            expires = None
        if request.form.get("unlimited"):
            unlimited = 1
        if request.form.get("duration"):
            duration = request.form.get("duration")
        if int(request.form.get("library_count")) > 0:
            specific_libraries = []
            library_count = int(request.form.get("library_count"))
            for library in range(library_count+1):

                if request.form.get("library_" + str(library)):
                    specific_libraries.append(request.form.get(
                        "library_" + str(library)))
            if not specific_libraries:
                specific_libraries = None
            else:
                specific_libraries = ', '.join(specific_libraries)
        Invitations.create(code=code, used=False, created=datetime.datetime.now(
        ).strftime("%Y-%m-%d %H:%M"), expires=expires, unlimited=unlimited, duration=duration, specific_libraries=specific_libraries)
        link = os.getenv("APP_URL") + "/j/" + code
        invitations = Invitations.select().order_by(Invitations.created.desc())
        return render_template("admin/invite.html", link=link, invitations=invitations, url=os.getenv("APP_URL"))
    else:
        invitations = Invitations.select().order_by(Invitations.created.desc())
        needUpdate()
        server_type = Settings.get(Settings.key == "server_type").value
        return render_template("admin/invite.html", invitations=invitations, update_msg=update_msg, needUpdate=needUpdate(), url=os.getenv("APP_URL"), server_type=server_type)


@app.route('/settings', methods=["GET", "POST"])
def preferences():

    if not Settings.select().where(Settings.key == 'server_type').exists():
        if request.method == 'GET':
            type = request.args.get("type")
            if type == 'jellyfin' or type == 'plex':
                Settings.create(key="server_type", value=type)
                return redirect("/settings")

            return render_template("server_type.html")
    elif not Settings.select().where(Settings.key == 'admin_username').exists():

        if request.method == 'GET':
            if request.args.get("type") == 'jellyfin' or request.args.get("type") == 'plex':
                Settings.update(value=request.args.get("type")).where(
                    Settings.key == "server_type").execute()
                logging.info("Server type set to " + request.args.get("type"))
                return redirect("/settings")
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

    elif not Settings.select().where(Settings.key == 'server_verified').exists():

        server_type = Settings.get(Settings.key == "server_type").value
        if request.method == 'GET':

            return render_template("verify-server.html", server_type=server_type)

        elif request.method == 'POST':
            server_name = request.form.get("server_name")
            server_url = request.form.get("server_url")
            api_key = request.form.get("api_key")
            overseerr_url = None
            discord_id = None

            # Getting Libraries Properly
            libraries = []

            library_count = int(request.form.get("library_count"))
            for library in range(library_count+1):

                if request.form.get("library_" + str(library)):
                    libraries.append(request.form.get(
                        "library_" + str(library)))
            libraries = ', '.join(libraries)
            if not libraries:
                return render_template("verify-server.html", error=_("You must select at least one library."), server_type=server_type)

            if request.form.get("discord_id"):
                discord_id = request.form.get("discord_id")
            if request.form.get("overseerr_url"):
                overseerr_url = request.form.get("overseerr_url")

            Settings.create(key="server_name", value=server_name)
            Settings.create(key="server_url", value=server_url)
            Settings.create(key="api_key", value=api_key)
            Settings.create(key="libraries", value=libraries)
            if overseerr_url:
                Settings.create(key="overseerr_url", value=overseerr_url)
            if discord_id:
                Settings.create(key="discord_id", value=discord_id)
            Settings.create(key="server_verified", value="True")
            return redirect("/")

    else:
        return redirect('/settings/')


@app.route('/settings/', methods=["GET", "POST"])
@login_required
def secure_settings():
    if request.method == 'GET':

        server_type = Settings.get(Settings.key == "server_type").value

        server_name = Settings.get(Settings.key == "server_name").value
        server_url = Settings.get(Settings.key == "server_url").value
        libraries = Settings.get(
            Settings.key == "libraries").value
        api_key = Settings.get(Settings.key == "api_key").value

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

        return render_template("admin/settings.html", server_name=server_name, server_url=server_url, server_type=server_type, api_key=api_key, overseerr_url=overseerr_url, discord_id=discord_id, custom_html=custom_html)

    elif request.method == 'POST':
        server_name = request.form.get("server_name")
        server_url = request.form.get("server_url")
        api_key = request.form.get("api_key")
        discord_id = None
        overseerr_url = None
        custom_html = None
        server_type = Settings.get(Settings.key == "server_type").value

        # Getting Libraries Properly
        libraries = []
        library_count = int(request.form.get("library_count"))
        for library in range(library_count+1):

            if request.form.get("library_" + str(library)):
                libraries.append(request.form.get(
                    "library_" + str(library)))
        libraries = ', '.join(libraries)

        if not libraries:
            libraries = Settings.get(Settings.key == "libraries").value

        if request.form.get("discord_id"):
            discord_id = request.form.get("discord_id")
        if request.form.get("overseerr_url"):
            overseerr_url = request.form.get("overseerr_url")
        if request.form.get("custom_html"):
            custom_html = request.form.get("custom_html")

        if server_type == "plex":
            try:
                plex = PlexServer(server_url, token=api_key)

            except Exception as e:
                logging.error(str(e))
                if "unauthorized" in str(e):
                    error = _("It is likely that your token does not work.")
                else:
                    error = _(
                        "Unable to connect to your Plex server. See Logs for more information.")
                return render_template("admin/settings.html", error=error)
        elif server_type == "jellyfin":
            headers = {
                "X-Emby-Token": api_key,
            }
            response = requests.get(
                f"{server_url}/Users", headers=headers)
            if response.status_code != 200:
                error = _("Unable to connect to your Jellyfin server.")
                return render_template("admin/settings.html", error=error)

        Settings.update(value=server_name).where(
            Settings.key == "server_name").execute()
        Settings.update(value=server_url).where(
            Settings.key == "server_url").execute()
        Settings.update(value=api_key).where(
            Settings.key == "api_key").execute()
        Settings.update(value=libraries).where(
            Settings.key == "libraries").execute()
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
        return render_template("admin/settings.html", server_name=server_name, server_url=server_url, server_type=server_type, api_key=api_key, overseerr_url=overseerr_url, discord_id=discord_id, custom_html=custom_html)


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
    return render_template("admin/invites.html")


@app.route('/invite/table/delete=<delete_code>', methods=["POST"])
@login_required
def table(delete_code):
    if delete_code != "None":
        Invitations.delete().where(Invitations.code == delete_code).execute()
    invitations = Invitations.select().order_by(Invitations.created.desc())
    for invite in invitations:
        if invite.expires and type(invite.expires) == str:
            invite.expires = datetime.datetime.strptime(
                invite.expires, "%Y-%m-%d %H:%M")
        if invite.expires and invite.expires.strftime("%Y-%m-%d %H:%M") < datetime.datetime.now().strftime("%Y-%m-%d %H:%M"):
            invite.expired = True
        else:
            invite.expired = False

    return render_template("tables/invite_table.html", invitations=invitations, rightnow=datetime.datetime.now())


@app.route('/users')
@login_required
def users():

    return render_template("admin/users.html")


@app.route('/users/table')
@login_required
def users_table():

    if request.args.get("delete"):
        print("Deleting user " + request.args.get("delete"))
        GlobalDeleteUser(request.args.get("delete"))
    users = None

    users = GlobalGetUsers()

    if Settings.get(Settings.key == "server_type").value == "plex":
        for user in users:
            user.expires = Users.get_or_none(Users.email == str(
                user.email)).expires if Users.get_or_none(Users.email == str(user.email)) else None
        return render_template("tables/user_table.html", users=users, rightnow=datetime.datetime.now())
    elif Settings.get(Settings.key == "server_type").value == "jellyfin":
        return render_template("tables/jellyfin_user_table.html", users=users, rightnow=datetime.datetime.now())


def needUpdate():
    try:
        r = requests.get(
            url="https://raw.githubusercontent.com/Wizarrrr/wizarr/master/.github/latest")
        data = r.content.decode("utf-8")
        if version.parse(VERSION) < version.parse(data):
            return True
        elif version.parse(VERSION) >= version.parse(data):
            return False
        else:
            return False
    except:
        return False


@scheduler.task('interval', id='checkExpiring', minutes=15, misfire_grace_time=900)
def checkExpiring():
    logging.info('Checking for expiring invites...')
    expiring = Users.select().where(
        Users.expires < datetime.datetime.now().strftime("%Y-%m-%d %H:%M"))
    for invite in expiring:
        GlobalDeleteUser(invite.used_by)
        logging.info("Deleting user " + invite.used_by +
                     " due to expired invite.")
    return
