from datetime import datetime
from functools import wraps
from logging import error, info, warning
from os import getenv
from secrets import token_hex

from flask import make_response, redirect, request, session
from flask_jwt_extended import current_user, jwt_required
from packaging import version
from playhouse.shortcuts import model_to_dict
from plexapi.myplex import PlexServer
from pydantic import HttpUrl
from requests import RequestException, get

from app import (Admins, APIKeys, Invitations, Libraries, Notifications,
                 Sessions, Settings)


def get_settings():
    # Get all settings from the database
    settings = {
        setting.key: setting.value
        for setting in Settings.select()
    }

    # Return all settings and notification agents
    return settings

def get_api_keys():
    # Get all API keys from the database
    admin_api_keys = list(APIKeys.select().where(APIKeys.user == current_user["id"]).execute())
    
    # Return all API keys
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


def scan_jellyfin_libraries(server_api_key: str, server_url: HttpUrl):
    # Add /Library/MediaFolders to Jellyfin URL
    api_url = str(server_url) + "Library/MediaFolders"
    
    # Get all libraries from Jellyfin
    headers = { "X-Emby-Token": server_api_key }
    response = get(url=api_url, headers=headers, timeout=30)
    
    # Raise exception if Jellyfin API returns non-200 status code
    if response.status_code != 200:
        raise RequestException(f"Jellyfin API returned {response.status_code} status code.")
    
    return response.json()["Items"]

def scan_plex_libraries(server_api_key: str, server_url: HttpUrl):
    # Get Plex URL as string
    api_url = str(server_url)
    
    # Get the libraries
    plex = PlexServer(api_url, server_api_key)
            
    # Get the raw libraries
    response: list[dict] = plex.library.sections()
    
    # Raise exception if raw_libraries is not a list
    if not isinstance(response, list):
        raise TypeError("Plex API returned invalid data.")
    
    return response


def need_update(VERSION: str):
    try:
        r = get(url="https://raw.githubusercontent.com/Wizarrrr/wizarr/master/.github/latest")
        data = r.content.decode("utf-8")
        return version.parse(VERSION) < version.parse(data)
    except Exception as e:
        info(f"Error checking for updates: {e}")
        return False