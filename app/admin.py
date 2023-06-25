from flask import request, redirect, render_template, make_response
from app import app, Invitations, Settings, session, Users, htmx, database
from app.plex import *
import secrets
from app.helpers import *
from app.notifications import *
from app.universal import *
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
    setup = Settings.get_or_none(Settings.key == "server_verified")
    if setup:
        print(setup.value)
        if setup.value == "True":
            return render_template("admin.html")
    return redirect('/settings')

@app.route('/admin/<path:path>')
@login_required
def admin_catch_all(path):
    setup = Settings.get_or_none(Settings.key == "server_verified")
    if setup:
        print(setup.value)
        if setup.value == "True":
            return render_template("admin.html")
    return redirect('/settings')


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
            plex_home = 1 if request.form.get("plex_home") else 0
            allowsync = 1 if request.form.get("allowsync") else 0
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
                plex_home=plex_home,
                duration=duration,
                specific_libraries=specific_libraries,
                plex_allow_sync=allowsync
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
            return render_template("admin/invite.html", needUpdate=need_update(), url=os.getenv("APP_URL"),
                                   server_type=server_type)
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
            hash = generate_password_hash(password, "scrypt")
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
                return render_template("verify-server.html", error=_("You must select at least one library."))

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

            return render_template("settings.html", **settings)
        else:
            return redirect("/admin")

    elif request.method == 'POST':
        server_type = request.form.get(
            "server_type", Settings.get(Settings.key == "server_type").value)
        server_name = request.form.get(
            "server_name", Settings.get(Settings.key == "server_name").value)
        server_url = request.form.get(
            "server_url", Settings.get(Settings.key == "server_url").value)
        api_key = request.form.get(
            "api_key", Settings.get(Settings.key == "api_key").value)
        libraries = []
        library_count = int(request.form.get("library_count", 0))
        for library in range(library_count + 1):
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
                return render_template("settings.html", error=error, )
        elif server_type == "jellyfin":
            headers = {
                "X-Emby-Token": api_key,
            }
            response = requests.get(f"{server_url}/Users", headers=headers)
            if response.status_code != 200:
                error = _("Unable to connect to your Jellyfin server.")
                return render_template("settings.html", error=error)

        with database.atomic():
            Settings.update(value=server_type).where(
                Settings.key == "server_type").execute()
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
            "server_type": server_type,
            "server_name": server_name,
            "server_url": server_url,
            "server_type": server_type,
            "api_key": api_key,
            "overseerr_url": overseerr_url,
            "ombi_api_key": ombi_api_key,
            "discord_id": discord_id,
            "custom_html": custom_html
        }

        return render_template("settings.html", **settings)


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

                # Migrate to scrypt from sha 256
                if Settings.get(Settings.key == "admin_password").value.startswith("sha256"): 
                    new_hash = generate_password_hash(password, method='scrypt')
                    Settings.update(value=new_hash).where(Settings.key == "admin_password").execute()

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
        if invite.expires and invite.expires.strftime("%Y-%m-%d %H:%M") < datetime.datetime.now().strftime(
            "%Y-%m-%d %H:%M"):
            invite.expired = True
        else:
            invite.expired = False

    return render_template("tables/invite_table.html", server_type=Settings.get(key="server_type").value,
                           invitations=invitations, rightnow=datetime.datetime.now())


@app.route('/settings/notifications', methods=["GET", "POST"])
@login_required
def notifications():
    if request.args.get("delete"):
        Notifications.delete().where(Notifications.id == request.args.get("delete")).execute()
    agents = Notifications.select()
    return render_template("admin/notifications.html", agents=agents)


@app.route('/settings/notifications/create', methods=["GET", "POST"])
@login_required
def create_notification():
    if request.method == "POST":
        form = {
            "name": request.form.get("name"),
            "url": request.form.get("url"),
            "notification_service": request.form.get("notification_service"),
            "username": request.form.get("username") if request.form.get("username") else None,
            "password": request.form.get("password") if request.form.get("password") else None,
            "userkey": request.form.get("userkey") if request.form.get("userkey") else None,
            "apitoken": request.form.get("apitoken") if request.form.get("apitoken") else None
        }
        
        if form["notification_service"] == "discord":
            if notify_discord("Wizarr here! Can you hear me?", form["url"]):
                Notifications.create(name=form["name"], url=form["url"], type=form["notification_service"])
                return redirect("/settings/notifications")
            else:
                resp = make_response(render_template("modals/create-notification-agent.html", error="Could Not "
                                                                                                    "Connect to "
                                                                                                    "Discord "
                                                                                                    "Webhook"))
                resp.headers['HX-Retarget'] = '#create-modal'
                return resp

        elif form["notification_service"] == "ntfy":
            if notify_ntfy("Wizarr here! Can you hear me?", "Wizarr", "tada", form["url"], username=form["username"],
                           password=form["password"]):
                Notifications.create(name=form["name"], url=form["url"], type=form["notification_service"],
                                     username=form["username"], password=form["password"])
                return redirect("/settings/notifications")
            else:
                print("error")
                resp = make_response(render_template("modals/create-notification-agent.html", error="Could "
                                                                                                    "not "
                                                                                                    "Connect "
                                                                                                    "to Ntfy"))
                resp.headers['HX-Retarget'] = '#create-modal'
                return resp
            
        elif form["notification_service"] == "pushover":
            if notify_pushover("Wizarr here! Can you hear me?", "Wizarr", form["url"], username=form["userkey"], password=form["apitoken"]):
                Notifications.create(name=form["name"], url=form["url"], type=form["notification_service"], username=form["userkey"], password=form["apitoken"])
                return redirect("/settings/notifications")
            else:
                print("error")
                resp = make_response(render_template("modals/create-notification-agent.html", error="Could not Connect to Pushover"))
                resp.headers['HX-Retarget'] = '#create-modal'
                return resp
            
    else:
        return render_template("modals/create-notification-agent.html")
    
    logging.info("A user created a new notification agent")


@app.route('/users')
@login_required
def users():
    return render_template("admin/users.html")


@app.route('/user/<user>', methods=["GET", "POST"])
@login_required
def user(user):
    if htmx:
        server_type = Settings.get(Settings.key == "server_type").value
        info = {}
        if server_type == "jellyfin":
            user_id = Users.get_by_id(user).token
            if request.method == "GET":
                info = Get(f"/Users/{user_id}").json()
                for key, value in info["Policy"].items():
                    if type(value) == list:
                        if not value:
                            info["Policy"][key] = ""
                        else:
                            # Slip value into a string
                            info["Policy"][key] = ", ".join(value)
                for key, value in info["Configuration"].items():
                    if type(value) == list:
                        if not value:
                            info["Configuration"][key] = ""
                        else:
                            # Slip value into a string
                            info["Configuration"][key] = ", ".join(value)

            elif request.method == "POST":
                info = Get(f"/Users/{user_id}").json()
                print(info["Policy"])
                for key, value in request.form.items():

                    for field in info["Policy"]:
                        if key == field:
                            if type(info["Policy"][field]) == bool:
                                if type(info["Policy"][field]) == bool:
                                    if value == "True":
                                        value = True
                                    else:
                                        value = False
                            if type(info["Policy"][field]) == int:
                                value = int(value)
                            if type(info["Policy"][field]) == list:
                                if value == "":
                                    value = []
                                else:
                                    value = value.split(", ")
                            info["Policy"][field] = value
                    for field in info["Configuration"]:

                        if key == field:
                            if type(info["Configuration"][field]) == bool:
                                if value == "True":
                                    value = True
                                else:
                                    value = False
                            if type(info["Configuration"][field]) == int:
                                value = int(value)
                            if type(info["Configuration"][field]) == list:
                                if value == "":
                                    value = []
                                else:
                                    value = value.split(", ")
                            info["Configuration"][field] = value
                response = Post(f"/Users/{user_id}", info)
                return redirect("/users/table")

        else:
            info = plex_get_user(user)
            if request.method == "POST":
                plex_token = Settings.get(Settings.key == "api_key").value
                plex_url = Settings.get(Settings.key == "server_url").value
                admin = MyPlexAccount(plex_token)
                server = PlexServer(plex_url, plex_token)
                username = info["Name"]
                for form in request.form.items():
                    print(form)
                response = admin.updateFriend(username, server, allowSync=bool(request.form.get("allowSync")),
                                              allowCameraUpload=bool(request.form.get("allowCameraUpload")),
                                              allowChannels=bool(request.form.get("allowChannels")))
                print(response)
                return redirect("/users/table")
        return render_template("admin/user.html", user=info, db_id=user)

    else:
        return redirect("/admin")


@app.route('/users/table')
@login_required
def users_table():
    if request.args.get("delete"):
        print("Deleting user " + request.args.get("delete"))
        global_delete_user(request.args.get("delete"))

    users = global_get_users()

    return render_template('tables/global-users.html', users=users)


def need_update():
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
def check_expiring():
    logging.info('Checking for expiring users...')
    expiring = Users.select().where(
        Users.expires < datetime.datetime.now().strftime("%Y-%m-%d %H:%M"))
    for user in expiring:
        global_delete_user(user)
        logging.info("Deleting user " + user.email +
                     " due to expired invite.")
    return
