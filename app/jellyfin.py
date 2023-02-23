import requests
import datetime
from app import *
from flask import abort, jsonify, render_template, redirect
import logging

API_KEY = Settings.get_or_none(Settings.key == "api_key").value if Settings.get_or_none(Settings.key == "api_key") else None
JELLYFIN_URL = Settings.get_or_none(Settings.key == "server_url").value if Settings.get_or_none(Settings.key == "server_url") else None


def Post(path, data):

    headers = {
        "X-Emby-Token": API_KEY,
    }
    response = requests.post(
        f"{JELLYFIN_URL}{path}", json=data, headers=headers)
    return response


def Get(path):

    headers = {
        "X-Emby-Token": API_KEY,
    }
    response = requests.get(
        f"{JELLYFIN_URL}{path}", headers=headers)
    return response


def jf_inviteUser(username, password, code, email):
    user = {
        "Name": username,
        "Password": password,
    }
    if Invitations.select().where(Invitations.code == code, Invitations.unlimited == 0):
        Invitations.update(used=True, used_at=datetime.datetime.now().strftime(
            "%Y-%m-%d %H:%M"), used_by=username).where(Invitations.code == code).execute()
    else:
        Invitations.update(used_at=datetime.datetime.now().strftime(
            "%Y-%m-%d %H:%M"), used_by=username).where(Invitations.code == code).execute()

    response = Post("/Users/New", user)
    logging.info("Invited " + username + " to Jellyfin Server")

    user_id = response.json()["Id"]

    sections = None
    if Invitations.select().where(Invitations.code == code, Invitations.specific_libraries != None):
        sections = list(
            (Invitations.get(Invitations.code == code).specific_libraries).split(", "))

    else:
        sections = list(
            (Settings.get(Settings.key == "libraries").value).split(", "))
    folders = {
        "EnableAllFolders": "false",
        "EnabledFolders": sections
    }
    response = Post(f"/Users/{user_id}/Policy", folders)
    Users.create(username=username, email=email,
                 password=password, token=user_id, code=code)
    return


@app.route('/jf-scan', methods=["POST"])
def jf_scan():
    jellyfin_url = request.args.get('jellyfin_url')
    api_key = request.args.get('jellyfin_api_key')
    if not jellyfin_url or not api_key:
        abort(400)
    try:
        response = Get("/Library/MediaFolders")
    except:
        abort(400)
    libraries = {}
    for library in response.json()["Items"]:

        libraries[library["Name"]] = library["Id"]
    return jsonify(libraries)


@app.route('/jf-scan-specific', methods=["POST"])
def jf_scan_specific():
    jellyfin_url = JELLYFIN_URL
    api_key = API_KEY
    if not jellyfin_url or not api_key:
        abort(400)
    try:
        response = Get("/Library/MediaFolders")
        libraries_raw = response.json()
    except:
        abort(400)
    libraries = {}
    for library in response.json()["Items"]:

        libraries[library["Name"]] = library["Id"]
    return jsonify(libraries)


@app.route('/setup/jellyfin', methods=["POST"])
def join_jellyfin():
    username = request.form.get('username')
    password = request.form.get('password')
    confirm_password = request.form.get('confirm-password')
    code = request.form.get('code')
    email = request.form.get("email")
    if not username or not password or not code or not email:
        return render_template("signup-jellyfin.html", username=username, email=email, code=code, error="Please fill out all fields")
    if password != confirm_password:
        return render_template("signup-jellyfin.html", username=username, email=email, code=code, error="Passwords do not match")
    if not Invitations.select().where(Invitations.code == code, Invitations.expires >= datetime.datetime.now()).exists():
        return render_template("signup-jellyfin.html", username=username, email=email, code=code, error="Invalid code")
    if Users.select().where(Users.username == username).exists():
        return render_template("signup-jellyfin.html", username=username, email=email, code=code, error="Username already exists")
    if Users.select().where(Users.email == email).exists():
        return render_template("signup-jellyfin.html", username=username, email=email, code=code, error="Email already exists")
    jf_inviteUser(username, password, code, email)
    return redirect('/setup')


def jf_GetUsers():
    response = Get("/Users")
    # Compare user to database
    for user in response.json():
        if not Users.select().where(Users.token == user["Id"]).exists():
            Users.create(username=user["Name"], email="empty",code="empty", password="empty", token=user["Id"])
    
    #Compare database to users
    for user in Users.select():
        if not any(d['Id'] == user.token for d in response.json()):
            user.delete_instance()
    return response.json()


def jf_DeleteUser(user):
    headers = {
        "X-Emby-Token": API_KEY,
    }
    response = requests.delete(
        f"{JELLYFIN_URL}/Users/{user}", headers=headers)
    return response
