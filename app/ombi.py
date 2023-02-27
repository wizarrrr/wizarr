import requests
import datetime
from app import *
from flask import abort, jsonify, render_template, redirect
import logging
import re

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
        f"{overseerr_url}/api/v1/Job/{name}UserImporter/", headers=headers, timeout=5)
    logging.info(f"POST {overseerr_url}/api/v1/Job/{name}UserImporter/ - {str(response.status_code)}")

    return response

def ombi_RunAllUserImporters():
    #ombi_RunUserImporter('plex')
    #ombi_RunUserImporter('emby')
    return ombi_RunUserImporter('jellyfin')

def ombi_DeleteUser(internal_user_token):
    if not Settings.get_or_none(Settings.key == "overseerr_url"):
        return
    if not Settings.get_or_none(Settings.key == "ombi_api_key"):
        return

    overseerr_url = Settings.get_or_none(Settings.key == "overseerr_url").value
    ombi_api_key = Settings.get_or_none(Settings.key == "ombi_api_key").value
    headers = {
        "ApiKey": ombi_api_key,
    }

    # Get the ombi users
    resp = requests.get(
        f"{overseerr_url}/api/v1/Identity/Users", headers=headers, timeout=5)

    # get the wizarr username from internal_user_token
    dbQuery = Users.select().where(Users.token == internal_user_token)
    for u in dbQuery:
        username=u.username

    # Match wizarr username with ombi username and get the ombi_user_id.
    ombi_user_id = None
    for user in resp.json():
        if user['userName'] == username:
            ombi_user_id = user['id']
            continue

    # Remove ombi user.
    if ombi_user_id:
        response = requests.delete(
            f"{overseerr_url}/api/v1/Identity/{ombi_user_id}", headers=headers, timeout=5)
        logging.info(f"DELETE {overseerr_url}/api/v1/Identity/{ombi_user_id} - {str(response.status_code)}")

        return response
    else:
        return