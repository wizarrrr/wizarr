import requests
import datetime

from password_strength import PasswordPolicy

from app import *
from app.notifications import notify
from app.helpers import is_invite_valid
from flask import abort, jsonify, render_template, redirect
import logging
import re
import time
from peewee import PeeweeException
from app.mediarequest import *

def Post(path, data):
    jellyfin_url = Settings.get_or_none(Settings.key == "server_url").value
    api_key = Settings.get_or_none(Settings.key == "api_key").value

    headers = {
        "X-Emby-Token": api_key,
    }
    response = requests.post(
        f"{jellyfin_url}{path}", json=data, headers=headers)
    logging.info("POST " + jellyfin_url + path + " " + str(response.status_code))
    return response


def Get(path):
    jellyfin_url = Settings.get_or_none(Settings.key == "server_url").value
    api_key = Settings.get_or_none(Settings.key == "api_key").value

    headers = {
        "X-Emby-Token": api_key,
    }
    response = requests.get(
        f"{jellyfin_url}{path}", headers=headers)
    return response

def jf_invite_user(username, password, code, email):
    try:
        # Create user dictionary
        user = {"Name": username, "Password": password}

        # Update invitation status
        invitation = Invitations.select().where(Invitations.code == code, Invitations.unlimited == 0).first()
        if invitation:
            invitation.used = True
            invitation.used_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            invitation.used_by = username
            invitation.save()
        else:
            Invitations.update(used_at=datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), used_by=username).where(Invitations.code == code).execute()

        # Create user and get user ID
        response = Post("/Users/New", user)
        user_id = response.json()["Id"]

        # Set user policy for libraries
        invitation = Invitations.select().where(Invitations.code == code, Invitations.specific_libraries != None).first()
        sections = list((invitation.specific_libraries).split(", ")) if invitation else list((Settings.get(Settings.key == "libraries").value).split(", "))
        policy = {"EnableAllFolders": False, "EnabledFolders": sections}
        try:
            response = Get(f"/Users/{user_id}")
            response.raise_for_status()
            policy.update(response.json()["Policy"])
        except Exception as e:
            logging.error(f"Error getting Jellyfin User Policy: {str(e)}")
            logging.error("Response was: ", response.json())
        Post(f"/Users/{user_id}/Policy", policy).raise_for_status()

        # Create user and set expiration date
        expires = (datetime.datetime.now() + datetime.timedelta(days=int(Invitations.get(code=code).duration))) if Invitations.get(code=code).duration else None
        Users.create(username=username, email=email, password=password, token=user_id, code=code, expires=expires)
        
        # Add user to Request Server
        mediarequest_import_users([user_id])
        
        # Notify admin of new user
        notify("New User", f"User {username} has joined your server!", "tada")

        # Update invitation status again
        if invitation:
            invitation.used = True
            invitation.used_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            invitation.used_by = email
            invitation.save()
        else:
            Invitations.update(used_at=datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), used_by=email).where(Invitations.code == code).execute()

        # Log invitation
        logging.info(f"Invited {username} to Jellyfin Server")
        return True


    except requests.exceptions.HTTPError as e:
        logging.error(f"Error {e.response.status_code} {e.response.reason}: {e.response.text}")
        return False
    except Exception as e:
        logging.error(f"Error: {str(e)}")
        return False


@app.route('/jf-scan', methods=["POST"])
def jf_scan():
    jellyfin_url = request.args.get('jellyfin_url')
    api_key = request.args.get('jellyfin_api_key')
    if not jellyfin_url or not api_key:
        logging.error("Jellyfin URL or API Key not set")
        abort(400)
    try:
        headers = {
            "X-Emby-Token": api_key,
        }
        response = requests.get(
            f"{jellyfin_url}/Library/MediaFolders", headers=headers)
    except Exception as e:
        logging.error("Error getting Jellyfin Libraries: " + str(e))
        abort(400)
    libraries = {}
    for library in response.json()["Items"]:

        libraries[library["Name"]] = library["Id"]
    return jsonify(libraries)


@app.route('/jf-scan-specific', methods=["POST"])
def jf_scan_specific():
    jellyfin_url = Settings.get_or_none(Settings.key == "server_url").value
    api_key = Settings.get_or_none(Settings.key == "api_key").value
    if not jellyfin_url or not api_key:
        abort(400)
    try:
        response = Get("/Library/MediaFolders")
        libraries_raw = response.json()
    except Exception as e:
        logging.error("Error getting Jellyfin Libraries: " + str(e))
        abort(400)
    libraries = {}
    for library in response.json()["Items"]:

        libraries[library["Name"]] = library["Id"]
    return jsonify(libraries)


@app.route('/setup/open-Jellyfin', methods=["GET"])
def open_jellyfin():
    jellyfin_url = Settings.get_or_none(Settings.key == "server_url").value
    return redirect(jellyfin_url)


@app.route('/setup/jellyfin', methods=["POST"])
def join_jellyfin():
    username = request.form.get('username')
    password = request.form.get('password')
    confirm_password = request.form.get('confirm-password')
    code = request.form.get('code')
    email = request.form.get("email")
    min_password_length = int(os.getenv("MIN_PASSWORD_LENGTH", "8"))
    max_password_length = int(os.getenv("MAX_PASSWORD_LENGTH", "20"))
    min_password_uppercase = int(os.getenv("MIN_PASSWORD_UPPERCASE", "1"))
    min_password_numbers = int(os.getenv("MIN_PASSWORD_NUMBERS", "1"))
    min_password_special = int(os.getenv("MIN_PASSWORD_SPECIAL", "0"))

    password_policy = PasswordPolicy.from_names(
        length=min_password_length,
        uppercase=min_password_uppercase,
        numbers=min_password_numbers,
        special=min_password_special,
    )

    if not (re.fullmatch(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b', email)):
        return render_template("welcome-jellyfin.html", username=username, email=email, code=code, error="Invalid email addres")

    if not username or not password or not code or not email:
        return render_template("welcome-jellyfin.html", username=username, email=email, code=code, error="Please fill out all fields",)

    # check password validity
    if not (min_password_length <= len(password) <= max_password_length):
        return render_template("welcome-jellyfin.html", username=username, email=email, code=code, error=f"Password must be between {min_password_length} and {max_password_length} characters")

    if len(password_policy.test(password)) > 0:
        return render_template("welcome-jellyfin.html", username=username, email=email, code=code, error=f"Password must contain {min_password_uppercase} uppercase, {min_password_numbers} numbers and {min_password_special} special characters")

    if password != confirm_password:
        return render_template("welcome-jellyfin.html", username=username, email=email, code=code, error="Passwords do not match")
    
    valid, message = is_invite_valid(code)
    if not valid:
        return render_template("welcome-jellyfin.html", username=username, email=email, code=code, error=message)
    
    jf_get_users()
    
    if Users.select().where(Users.username == username).exists():
        return render_template("welcome-jellyfin.html", username=username, email=email, code=code, error="User already exists")
    if Users.select().where(Users.email == email).exists():
        return render_template("welcome-jellyfin.html", username=username, email=email, code=code, error="Email already exists")
    
    if jf_invite_user(username, password, code, email):
        return redirect('/setup')
    else:
        return render_template("welcome-jellyfin.html", username=username, email=email, code=code, error="An error occured. Please contact an administrator.")


def jf_get_users():
    response = Get("/Users")
    # Compare user to database
    for user in response.json():
        if not Users.select().where(Users.token == user["Id"]).exists():
            Users.create(username=user["Name"], email="empty",
                         code="empty", password="empty", token=user["Id"])

    # Compare database to users
    if Users.select():
        for user in Users.select():
            if not any(d['Id'] == user.token for d in response.json()):
                user.delete_instance()
    users = Users.select()    
    
    if not users:
        abort(400)

    # Add photo to users
    for user in users:
        jellyfin_url = Settings.get_or_none(Settings.key == "server_url").value
        user.photo = f"{jellyfin_url}/Users/{user.token}/Images/Primary?maxHeight=150&maxWidth=150&tag=%7Btag%7D&quality=30"
    
    return users

def jf_delete_user(user):
    try:
        jf_id = Users.get_by_id(user).token
        jellyfin_url = Settings.get(Settings.key == "server_url").value
        api_key = Settings.get(Settings.key == "api_key").value
        headers = {
            "X-Emby-Token": api_key,
        }
        response = requests.delete(
            f"{jellyfin_url}/Users/{jf_id}", headers=headers)
        response.raise_for_status()  # raise exception for non-2xx status codes
        return response
    except (PeeweeException, requests.exceptions.RequestException) as e:
        logging.error(f"Error deleting Jellyfin user {user}: {str(e)}")
        return None  # or return some other value indicating failure