from flask import request, redirect, render_template
from app import app, Invitations, Settings, session, Users, htmx, database
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
    if htmx:
        if request.method == "POST":
            try:
                code = request.form.get("code").upper()
                if len(code) != 6:
                    return abort(401)
            except:
                code = ''.join(secrets.choice(
                    string.ascii_uppercase + string.digits) for _ in range(6))
            if Invitations.get_or_none(code=code):
                return abort(401)  # Already Exists

            # Set invitation attributes
            expires_options = {
                "day": (datetime.datetime.now() + datetime.timedelta(days=1)),
                "week": (datetime.datetime.now() + datetime.timedelta(days=7)),
                "month": (datetime.datetime.now() + datetime.timedelta(days=30)),
                "never": None
            }
            expires = expires_options.get(request.form.get("expires"))
            unlimited = 1 if request.form.get("unlimited") else 0
            duration = request.form.get("duration")
            specific_libraries = None
            library_count = int(request.form.get("library_count", 0))
            if library_count > 0:
                specific_libraries = ', '.join(filter(None, [
                    request.form.get("library_" + str(library))
                    for library in range(library_count + 1)
                ]))

            # Create invitation
            Invitations.create(
                code=code,
                used=False,
                created=datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                expires=expires.strftime(
                    "%Y-%m-%d %H:%M:%S") if expires else None,
                unlimited=unlimited,
                duration=duration,
                specific_libraries=specific_libraries
            )
            link = os.getenv("APP_URL") + "/j/" + code

            # Retrieve invitations
            invitations = Invitations.select().order_by(Invitations.created.desc())

            # Render template
            return render_template(
                "admin/invite.html",
                link=link,
                invitations=invitations,
                url=os.getenv("APP_URL")
            )
        else:
            server_type = Settings.get(Settings.key == "server_type").value
            return render_template("admin/invite.html", needUpdate=needUpdate(), url=os.getenv("APP_URL"), server_type=server_type)
    else:
        return redirect("/admin")


@app.route('/settings', methods=["GET", "POST"])
def preferences():

    settings = {
        'server_type': None,
        'admin_username': None,
        'server_verified': None,
        'admin_password': None,
        'server_url': None,
        'api_key': None,
        'server_name': None,
        'libraries': None,
        'overseerr_url': None,
        'ombi_api_key': None,
        'discord_id': None,
        'server_verified': None,
    }

    for key in settings.keys():
        obj, created = Settings.get_or_create(key=key)
        if created:
            obj.save()
        settings[key] = obj

    if not settings['admin_username'].value or not settings['admin_password'].value:

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
            settings['admin_username'].value = username
            settings['admin_username'].save()
            settings['admin_password'].value = hash
            settings['admin_password'].save()
            return redirect('/settings')

    elif not settings['server_verified'].value:

        if request.method == 'GET':

            return render_template("verify-server.html")

        elif request.method == 'POST':
            server_name = request.form.get("server_name")
            server_type = request.form.get("server_type")
            server_url = request.form.get("server_url")
            api_key = request.form.get("api_key")
            overseerr_url = request.form.get("overseerr_url")
            ombi_api_key = request.form.get("ombi_api_key")
            discord_id = request.form.get("discord_id")
            libraries = [request.form.get("library_{}".format(i)) for i in range(int(
                request.form.get("library_count")) + 1) if request.form.get("library_{}".format(i))]
            if not libraries:
                return render_template("verify-server.html", error=_("You must select at least one library."), server_type=server_type)

            settings['server_name'].value = server_name
            settings['server_name'].save()
            settings['server_type'].value = server_type
            settings['server_type'].save()
            settings['server_url'].value = server_url
            settings['server_url'].save()
            settings['api_key'].value = api_key
            settings['api_key'].save()
            settings['libraries'].value = ', '.join(libraries)
            settings['libraries'].save()
            if overseerr_url:
                settings['overseerr_url'].value = overseerr_url
                settings['overseerr_url'].save()
            if ombi_api_key:
                settings['ombi_api_key'].value = ombi_api_key
                settings['ombi_api_key'].save()
            if discord_id:
                settings['discord_id'].value = discord_id
                settings['discord_id'].save()
            settings['server_verified'].value = True
            settings['server_verified'].save()
            return redirect('/admin')
    else:
        return redirect('/admin')


@app.route('/settings/', methods=["GET", "POST"])
@login_required
def secure_settings():

    if request.method == 'GET':
        if htmx:
            settings = {}
            for s in Settings.select():
                settings[s.key] = s.value

            return render_template("admin/settings.html", **settings)
        else:
            return redirect("/admin")

    elif request.method == 'POST':
        server_type = Settings.get(Settings.key == "server_type").value
        server_name = request.form.get(
            "server_name", Settings.get(Settings.key == "server_name").value)
        server_url = request.form.get(
            "server_url", Settings.get(Settings.key == "server_url").value)
        api_key = request.form.get(
            "api_key", Settings.get(Settings.key == "api_key").value)
        libraries = []
        library_count = int(request.form.get("library_count", 0))
        for library in range(library_count+1):
            library_value = request.form.get(f"library_{library}")
            if library_value:
                libraries.append(library_value)
        libraries = ', '.join(libraries) or Settings.get(
            Settings.key == "libraries").value
        overseerr_url = request.form.get("overseerr_url", None)
        ombi_api_key = request.form.get("ombi_api_key", None)
        discord_id = request.form.get("discord_id", None)
        custom_html = request.form.get("custom_html", None)

        if server_type == "plex":
            try:
                PlexServer(server_url, token=api_key)
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
            response = requests.get(f"{server_url}/Users", headers=headers)
            if response.status_code != 200:
                error = _("Unable to connect to your Jellyfin server.")
                return render_template("admin/settings.html", error=error)

        with database.atomic():
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
            else:
                Settings.delete().where(Settings.key == "overseerr_url").execute()
            if ombi_api_key:
                Settings.delete().where(Settings.key == "ombi_api_key").execute()
                Settings.create(key="ombi_api_key", value=ombi_api_key)
            else:
                Settings.delete().where(Settings.key == "ombi_api_key").execute()
            if discord_id:
                Settings.delete().where(Settings.key == "discord_id").execute()
                Settings.create(key="discord_id", value=discord_id)
            else:
                Settings.delete().where(Settings.key == "discord_id").execute()
            if custom_html:
                Settings.delete().where(Settings.key == "custom_html").execute()
                Settings.create(key="custom_html", value=custom_html)
            else:
                Settings.delete().where(Settings.key == "custom_html").execute()

        settings = {
            "server_name": server_name,
            "server_url": server_url,
            "server_type": server_type,
            "api_key": api_key,
            "overseerr_url": overseerr_url,
            "ombi_api_key": ombi_api_key,
            "discord_id": discord_id,
            "custom_html": custom_html
        }

        return render_template("admin/settings.html", **settings)


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
    if htmx:
        return render_template("admin/invites.html")
    else:
        return redirect("/admin")


@app.route('/invite/table', methods=["POST"])
@login_required
def table():
    if request.args.get("delete"):
        Invitations.delete().where(Invitations.code == request.args.get("delete")).execute()
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

@app.route('/user/<user>', methods=["GET", "POST"])
@login_required
def user(user):
    if htmx:
        if request.method == "POST":
            info = Get(f"/Users/{user}").json()
            print(info["Policy"])
            for key, value in request.form.items():
                
                for field in info["Policy"]:
                    if key == field:
                        info["Policy"][field] = value
                for field in info["Configuration"]:
                    if key == field:
                        info["Configuration"][field] = value
            print(info["Policy"])
            Post(f"/Users/{user}/Configuration", info["Configuration"])
            Post(f"/Users/{user}/Policy", info["Policy"])
            return redirect("/users/table")
                
        info = Get(f"/Users/{user}").json()
        return render_template("admin/user.html", user=info)
    else:
        return redirect("/admin")

@app.route('/users/table')
@login_required
def users_table():

    if request.args.get("delete"):
        print("Deleting user " + request.args.get("delete"))
        GlobalDeleteUser(request.args.get("delete"))
    users = None

    users = GlobalGetUsers()
    db_users = Users.select()

    if Settings.get(Settings.key == "server_type").value == "plex":
        for user in users:
            user.expires = Users.get_or_none(Users.email == str(
                user.email)).expires if Users.get_or_none(Users.email == str(user.email)) else None
            user.code = Users.get_or_none(Users.email == str(
                user.email)).code if Users.get_or_none(Users.email == str(user.email)) else None
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
