from datetime import datetime
from functools import wraps
from logging import error, info, warning
from os import getenv
from secrets import token_hex

from flask import make_response, redirect, session
from packaging import version
from requests import RequestException, get

from app import (Admins, APIKeys, Invitations, Libraries, Notifications,
                 Sessions, Settings)


def check_logged_in():
    admin_key = session.get("admin").get("key") if session.get("admin") else None
    admin = Sessions.get_or_none(session=admin_key)
    return admin is not None and admin_key == admin.session

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if check_logged_in():
            return f(*args, **kwargs)
        elif getenv("DISABLE_BUILTIN_AUTH") == "true":
            session["admin"] = { "id": 0, "username": "Anonymous", "key": token_hex(32) }
            return f(*args, **kwargs)
        else:
            return redirect("/login")

    return decorated_function


def api_key_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not Settings.get_or_none(Settings.key == "api_key"):
            return redirect('/settings')
        if not session.get("api_key"):
            return redirect("/login")
        if session.get("api_key") == Settings.get(Settings.key == "api_key").value:
            return f(*args, **kwargs)
        else:
            return redirect("/login")

    return decorated_function


def json_or_partial(request):
    hx_request = request.headers.get(
        "HX-Request") == "true" if "HX-Request" in request.headers else None
    rendered = request.headers.get(
        "rendered") == "true" if "rendered" in request.headers else None
    return False if hx_request is None and rendered is None else True if hx_request is None and rendered is not True else True if hx_request is True and rendered is None else True if hx_request is True and rendered is not True else False if hx_request is False and rendered is None else True if hx_request is False and rendered is not True else None


def get_settings():
    # Get all settings from the database
    settings = {
        setting.key: setting.value
        for setting in Settings.select()
    }

    # Return all settings and notification agents
    return settings

def get_api_keys():
    admin = session.get("admin")
    admin_id = admin.get("id")
    admin_key = admin.get("key")

    if not admin_id or not admin_key:
        return False

    admin = Admins.get_or_none(id=admin_id)
    admin_api_keys = list(APIKeys.select().where(APIKeys.user == admin).execute())

    return admin_api_keys

def get_notifications():
    # Get all notification agents from the database
    notifications = Notifications.select()

    # Return all notification agents
    return notifications


def is_invite_valid(code):
    invitation = Invitations.get_or_none(Invitations.code == code)
    if not invitation:
        return False, "Invalid code"
    if invitation.expires and invitation.expires <= datetime.now():
        return False, "Invitation has expired."
    if invitation.used is True and invitation.unlimited is not True:
        return False, "Invitation has already been used."
    return True, "okay"


def scan_jellyfin_libraries(server_api_key: str, server_url: str):
    try:
        headers = { "X-Emby-Token": server_api_key }
        response = get(f"{server_url}/Library/MediaFolders", headers=headers, timeout=10)
        return response.json()["Items"]
    except RequestException as e:
        error(f"Error scanning Jellyfin libraries: {e}")
        return None
    
def need_update(VERSION: str):
    try:
        r = get(url="https://raw.githubusercontent.com/Wizarrrr/wizarr/master/.github/latest")
        data = r.content.decode("utf-8")
        return version.parse(VERSION) < version.parse(data)
    except Exception as e:
        info(f"Error checking for updates: {e}")
        return False