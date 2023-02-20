import logging
from re import I
import secrets
import string
import os
import os.path
import requests
import datetime
from flask import request, redirect, render_template, abort, make_response, send_from_directory
from app import app, Invitations, Settings, VERSION, Oauth, get_locale
from app.plex import *
from app.admin import login_required
from flask_babel import _
from packaging import version
import threading


@app.route('/')
def redirect_to_invite():
    if not Settings.select().where(Settings.key == 'admin_username').exists():
        return redirect('/settings')
    return redirect('/invite')


@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')


@app.route("/j/<code>", methods=["GET"])
def plex(code):
    if not Invitations.select().where(Invitations.code == code).exists():
        return render_template('401.html'), 401
    name = Settings.get_or_none(
        Settings.key == "plex_name")
    if name:
        name = name.value
    else:
        name = "Wizarr"
    resp = make_response(render_template(
        'user-plex-login.html', name=name, code=code))
    resp.set_cookie('code', code)
    return resp


@app.route("/join", methods=["POST"])
def connect():
    code = request.form.get('code')
    if not Invitations.select().where(Invitations.code == code).exists():
        return render_template("user-plex-login.html", name=Settings.get(Settings.key == "plex_name").value, code=code, code_error="That invite code does not exist.")
    if Invitations.select().where(Invitations.code == code, Invitations.used == True, Invitations.unlimited == False).exists():
        return render_template("user-plex-login.html", name=Settings.get(Settings.key == "plex_name").value, code=code, code_error="That invite code has already been used.")
    if Invitations.select().where(Invitations.code == code, Invitations.expires <= datetime.datetime.now()).exists():
        return render_template("user-plex-login.html", name=Settings.get(Settings.key == "plex_name").value, code=code, code_error="That invite code has expired.")

    oauth = Oauth.create()
    threading.Thread(target=plexoauth, args=(oauth.id, code)).start()
    while not Oauth.get_by_id(oauth.id).url:
        pass
    return redirect(Oauth.get_by_id(oauth.id).url)


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
                       datetime.timedelta(days=1)).strftime("%Y-%m-%d %H:%M")
        if request.form.get("expires") == "week":
            expires = (datetime.datetime.now() +
                       datetime.timedelta(days=7)).strftime("%Y-%m-%d %H:%M")
        if request.form.get("expires") == "month":
            expires = (datetime.datetime.now() +
                       datetime.timedelta(days=30)).strftime("%Y-%m-%d %H:%M")
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

                if request.form.get("plex_library_" + str(library)):
                    specific_libraries.append(request.form.get(
                        "plex_library_" + str(library)))
            if not specific_libraries:
                specific_libraries = None
            else:
                specific_libraries = ', '.join(specific_libraries)
        Invitations.create(code=code, used=False, created=datetime.datetime.now(
        ).strftime("%Y-%m-%d %H:%M"), expires=expires, unlimited=unlimited, duration=duration, specific_libraries=specific_libraries)
        link = os.getenv("APP_URL") + "/j/" + code
        invitations = Invitations.select().order_by(Invitations.created.desc())
        return render_template("invite.html", link=link, invitations=invitations, url=os.getenv("APP_URL"))
    else:
        invitations = Invitations.select().order_by(Invitations.created.desc())
        needUpdate()
        return render_template("invite.html", invitations=invitations, update_msg=update_msg, needUpdate=needUpdate(), url=os.getenv("APP_URL"))


@app.route('/setup', methods=["GET"])
def setup():
    resp = make_response(render_template("wizard.html"))
    resp.set_cookie('current', "0")

    return resp


@app.route('/setup/open-plex', methods=["GET"])
def open_plex():
    return redirect('https://app.plex.tv/desktop/#!/')


@app.route('/setup/action=<action>', methods=["POST"])
def wizard(action):
    video_lang = get_locale()
    videos = {
        "en": {
            "web_video": "https://www.youtube.com/embed/yO_oPny-Y_I",
            "app_video": "https://www.youtube.com/embed/e7Gy4FHDy5k"
        },
        "fr": {

            "web_video": "https://www.youtube.com/embed/f1ce3_OY5OE",
            "app_video": "https://www.youtube.com/embed/u8ejqsGfntw"
        }
    }
    if video_lang not in videos:
        video_lang = "en"
    current = int(request.cookies.get('current'))

    discord_id_setting = Settings.get_or_none(Settings.key == "discord_id")
    overseerr_url_setting = Settings.get_or_none(
        Settings.key == "overseerr_url")
    custom_html_setting = Settings.get_or_none(Settings.key == "custom_html")
    discord_id = None
    overseerr_url = None
    custom_html = None

    steps = ["wizard/download.html", "wizard/tips.html"]
    if overseerr_url_setting:
        steps.insert((len(steps)-1), "wizard/requests.html")
        overseerr_url = Settings.get(Settings.key == "overseerr_url").value
    if discord_id_setting:
        steps.insert((len(steps)-1), "wizard/discord.html")
        discord_id = Settings.get(Settings.key == "discord_id").value
    if custom_html_setting:
        steps.insert((len(steps)-1), "wizard/custom.html")
        custom_html = Settings.get(Settings.key == "custom_html").value

    if action == "next":

        resp = make_response(render_template(
            steps[current+1], videos=videos,
            video_lang=video_lang,
            discord_id=discord_id,
            overseerr_url=overseerr_url,
            custom_html=custom_html,
            next=True))

        # Check if no next step
        if current+1 == len(steps)-1:
            resp.headers['max'] = "1"
            return resp
        else:
            resp.headers['max'] = "0"

        resp.headers['current'] = str(current+1)
        resp.set_cookie('current', str(current+1))
        return resp

    elif action == "prev":

        # Add current variable to header
        resp = make_response(render_template(
            steps[current-1], videos=videos,
            video_lang=video_lang,
            discord_id=discord_id,
            overseerr_url=overseerr_url,
            custom_html=custom_html,
            prev=True))
        resp.headers['current'] = str(current-1)
        resp.headers['max'] = "0"
        resp.set_cookie('current', str(current-1))
        return resp


@app.errorhandler(500)
def server_error(e):
    logging.error(e)
    return render_template('500.html'), 500


@app.errorhandler(404)
def server_error(e):
    logging.error(e)
    return render_template('404.html'), 404


@app.errorhandler(401)
def server_error(e):
    logging.error(e)
    return render_template('401.html'), 401


@app.context_processor
def inject_user():
    name = ""
    try:
        name = Settings.get(Settings.key == "plex_name").value
    except:
        name = "Wizarr"
        print("Could not find name :( ")
    return dict(header_name=name)
