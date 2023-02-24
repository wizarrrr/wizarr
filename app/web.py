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
    if Settings.get(key="server_type").value == "jellyfin":
        return render_template("signup-jellyfin.html", code=code)
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






@app.route('/setup', methods=["GET"])
def setup():
    resp = make_response(render_template("wizard.html", server_type=Settings.get(Settings.key == "server_type").value))
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
    server_type = Settings.get(Settings.key == "server_type").value

    steps = [f"wizard/{server_type}/download.html",]
    if overseerr_url_setting:
        steps.append("wizard/requests.html")
        overseerr_url = Settings.get(Settings.key == "overseerr_url").value
    if discord_id_setting:
        steps.append("wizard/discord.html")
        discord_id = Settings.get(Settings.key == "discord_id").value
    if custom_html_setting:
        steps.append("wizard/custom.html")
        custom_html = Settings.get(Settings.key == "custom_html").value
    
    steps.append("wizard/plex/tips.html") 
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
        name = Settings.get(Settings.key == "server_name").value
    except:
        name = "Wizarr"
        print("Could not find name :( ")
    return dict(header_name=name)
