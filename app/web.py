import logging
from re import I
import os
import os.path
import datetime
from flask import request, redirect, render_template, abort, make_response, send_from_directory
from app import app, Invitations, Settings, VERSION, get_locale
from app.plex import *
from flask_babel import _
import threading
import requests


@app.route('/')
def redirect_to_invite():
    if not Settings.select().where(Settings.key == 'admin_username').exists():
        return redirect('/settings')
    return redirect('/admin')


@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')


@app.route("/j/<code>", methods=["GET"])
def plex(code):
    if Settings.get(key="server_type").value == "jellyfin":
        return render_template("welcome-jellyfin.html", code=code)
    if not Invitations.select().where(Invitations.code == code).exists():
        return render_template('401.html'), 401
    name = Settings.get_or_none(
        Settings.key == "server_name")
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
    token = request.form.get("token")
    if not Invitations.select().where(Invitations.code == code).exists():
        return render_template("user-plex-login.html", name=Settings.get(Settings.key == "server_name").value, code=code, code_error="That invite code does not exist.")
    if Invitations.select().where(Invitations.code == code, Invitations.used == True, Invitations.unlimited == False).exists():
        return render_template("user-plex-login.html", name=Settings.get(Settings.key == "server_name").value, code=code, code_error="That invite code has already been used.")
    if Invitations.select().where(Invitations.code == code, Invitations.expires <= datetime.datetime.now()).exists():
        return render_template("user-plex-login.html", name=Settings.get(Settings.key == "server_name").value, code=code, code_error="That invite code has expired.")

    if Settings.get(key="server_type").value == "plex":
        threading.Thread(target=handleOauthToken, args=(token, code)).start()
        return redirect(os.getenv("APP_URL") + "/setup")

    elif Settings.get(key="server_type").value == "jellyfin":
        return render_template("signup-jellyfin.html", code=code)

def ombi_RunUserImporter(name):
    if not Settings.get_or_none(Settings.key == "overseerr_url"):
        return
    if not Settings.get_or_none(Settings.key == "ombi_api_key"):
        return

    overseerr_url = Settings.get_or_none(Settings.key == "overseerr_url").value
    ombi_api_key = Settings.get_or_none(Settings.key == "ombi_api_key").value
    headers = {
        "ApiKey": ombi_api_key,
    }
    response = requests.post(
        f"{overseerr_url}/api/v1/Job/{name}UserImporter/", headers=headers)
    logging.info(f"POST {overseerr_url}/api/v1/Job/{name}UserImporter/ - {str(response.status_code)}")

    return response

def ombi_RunAllUserImporters():
    #ombi_RunUserImporter('plex')
    #ombi_RunUserImporter('emby')
    return ombi_RunUserImporter('jellyfin')

@app.route('/setup', methods=["GET"])
def setup():
    ombi_RunAllUserImporters()

    resp = make_response(render_template(
        "wizard.html", server_type=Settings.get(Settings.key == "server_type").value))
    resp.set_cookie('current', "0")

    return resp


@app.route('/setup/open-plex', methods=["GET"])
def open_plex():
    return redirect('https://app.plex.tv/desktop/#!/')


@app.route('/setup/action=<action>', methods=["POST"])
def wizard(action):
    # Get video language and URL based on language
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
    

    # Get current step from cookies
    current = int(request.cookies.get('current'))

    # Get settings from database
    settings = {}
    for setting in Settings.select():
        settings[setting.key] = setting.value

    server_type = settings.get("server_type", "")

    # Build list of steps
    steps = [f"wizard/{server_type}/download.html",]

    if settings.get("overseerr_url"):
        steps.append("wizard/requests.html")

    if settings.get("discord_id"):
        steps.append("wizard/discord.html")

    if settings.get("custom_html"):
        steps.append("wizard/custom.html")

    steps.append(f"wizard/{server_type}/tips.html")

    # Render template for next or previous step
    if action == "next":
        next_step = current + 1
        max_step = len(steps) - 1
        resp = make_response(render_template(
            steps[next_step], videos=videos,
            video_lang=video_lang,
            discord_id=settings.get("discord_id"),
            overseerr_url=settings.get("overseerr_url"),
            custom_html=settings.get("custom_html"),
            next=True))
        resp.headers['current'] = str(next_step)
        resp.headers['max'] = "1" if next_step == max_step else "0"
        resp.set_cookie('current', str(next_step))
        return resp

    elif action == "prev":
        prev_step = current - 1
        resp = make_response(render_template(
            steps[prev_step], videos=videos,
            video_lang=video_lang,
            discord_id=settings.get("discord_id"),
            overseerr_url=settings.get("overseerr_url"),
            custom_html=settings.get("custom_html"),
            prev=True))
        resp.headers['current'] = str(prev_step)
        resp.headers['max'] = "0"
        resp.set_cookie('current', str(prev_step))
        return resp


@app.errorhandler(500)
def server_error(e):
    logging.error(e)
    return render_template('error/500.html'), 500


@app.errorhandler(404)
def server_error(e):
    logging.error(e)
    return render_template('error/404.html'), 404


@app.errorhandler(401)
def server_error(e):
    logging.error(e)
    return render_template('error/401.html'), 401


@app.context_processor
def inject_user():
    name = ""
    try:
        name = Settings.get(Settings.key == "server_name").value
    except:
        name = "Wizarr"
        print("Could not find name :( ")
    return dict(header_name=name)