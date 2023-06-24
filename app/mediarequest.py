import requests
import datetime
from app import *
from flask import abort, jsonify, render_template, redirect
import logging
import re

def get_settings():
    settings = {
        setting.key: setting.value
        for setting in Settings.select().where(
            (Settings.key == "request_url") | (Settings.key == "request_api_key") | (Settings.key == "server_type") | (Settings.key == "request_type")
        )
    }
    
    return settings

def mediarequest_import_users(users):
    settings = {
        setting.key: setting.value
        for setting in Settings.select().where(
            (Settings.key == "server_type") | (Settings.key == "request_url") | (Settings.key == "request_type")
        )
    }
    
    server_type = settings.get("server_type")
    request_type = settings.get("request_type")
    
    # Check if we have a request server setup
    if not request_type:
        logging.info("No request server setup")
        return
    
    # Make sure we are not attempting to import users from incompatible media servers to incompatible request servers
    if server_type == "plex" and request_type == "jellyseerr":
        logging.info("Jellyseerr is not supported for plex")
        return
    
    if server_type == "jellyfin" and request_type == "overseerr":
        logging.info("Overseerr is not supported for jellyfin")
        return
    
    # Run the correct import function based on the request type
    if request_type == "ombi":
        logging.info("Starting ombi user import")
        ombi_import_users()
        return
        
    if request_type == "overseerr":
        logging.info("Starting overseerr user import")
        overseerr_import_users(users)
        return
        
    if request_type == "jellyseerr":
        logging.info("Starting jellyseerr user import")
        jellyseerr_import_users(users)
        return
    
    # If we get here then something went wrong
    logging.error("Invalid operation")

def mediarequest_delete_users(users):
    settings = get_settings()
    
    server_type = settings.get("server_type")
    request_type = settings.get("request_type")
    
    # Check if we have a request server setup
    if not request_type:
        logging.info("No request server setup")
        return
    
    # Make sure we are not attempting to delete users from incompatible media servers to incompatible request servers
    if server_type == "plex" and request_type == "jellyseerr":
        logging.info("Jellyseerr is not supported for plex")
        return
    
    if server_type == "jellyfin" and request_type == "overseerr":
        logging.info("Overseerr is not supported for jellyfin")
        return
    
    # Run the correct import function based on the request type
    if request_type == "ombi":
        ombi_delete_users(users)
        return
        
    if request_type == "overseerr":
        overseerr_delete_user(users)
        return
        
    if request_type == "jellyseerr":
        jellyseerr_delete_user(users)
        return
    
    # If we get here then something went wrong
    logging.error("Invalid operation")
    

#
# Functions for importing users from jellyfin and plex to ombi, jellyfin and plex
#

def ombi_import_users():
    settings = get_settings()
    
    request_url = settings.get("request_url")
    request_api_key = settings.get("request_api_key")
    
    server_type = settings.get("server_type")
    
    # If no request_url or request_api_key is set, return
    if not request_url or not request_api_key:
        logging.info("No request_url or request_api_key set")
        return
    
    headers = {
        "ApiKey": request_api_key,
    }
    
    try:
        response = requests.post(f"{request_url}/api/v1/Job/{server_type}userimporter/", headers=headers, timeout=5)
        logging.info(f"POST {request_url}/api/v1/Job/{server_type}userimporter/ - {str(response.status_code)}")

        return response
    except Exception as e:
        logging.error("Error running ombi user importer: " + str(e))
        return
    
    
def overseerr_import_users(users):
    settings = get_settings()

    request_url = settings.get("request_url")
    request_api_key = settings.get("request_api_key")
    
    # If no request_url or request_api_key is set, return
    if not request_url or not request_api_key:
        logging.info("No request_url or request_api_key set")
        return
        
    headers = {
        "X-Api-Key": request_api_key,
        "Content-Type": "application/json",
    }
        
    # Loop through the users and make sure they are all strings
    users = [str(user) for user in users]
        
    # Create a dict with the users to import
    user_ids = {"plexIds": users}
        
    # Make the request to import the users to overseerr
    try:
        response = requests.post(f"{request_url}/api/v1/user/import-from-plex", json=user_ids, headers=headers, timeout=5)
        logging.info(f"POST {request_url}/api/v1/user/import-from-plex - {str(response.status_code)}")
        return response
        
    except Exception as e:
        logging.error("Error running overseerr user importer: " + str(e))
        return
    
def jellyseerr_import_users(users):
    settings = get_settings()

    request_url = settings.get("request_url")
    request_api_key = settings.get("request_api_key")

    # If no request_url or request_api_key is set, return
    if not request_url or not request_api_key:
        logging.info("No request_url or request_api_key set")
        return
        
    headers = {
        "X-Api-Key": request_api_key,
        "Content-Type": "application/json",
    }
        
    # Loop through the users and make sure they are all strings
    users = [str(user) for user in users]
        
    # Create a dict of the users to import
    user_ids = {"jellyfinUserIds": users}
        
     # Make the request to import the users to jellyseerr
    try:
        response = requests.post(f"{request_url}/api/v1/user/import-from-jellyfin", json=user_ids, headers=headers, timeout=20)
        logging.info(f"POST {request_url}/api/v1/user/import-from-jellyfin - {str(response.status_code)}")
        return response
        
    except Exception as e:
         logging.error("Error running jellyseerr user importer: " + str(e))
         return

    
#
# Functions for deleting users from ombi, overseerr and jellyseerr
#

def ombi_delete_users(internal_user_id):
    settings = get_settings()
    
    request_url = settings.get("request_url")
    request_api_key = settings.get("request_api_key")
    
    headers = {
        "ApiKey": request_api_key,
        "Content-Type": "application/json",
    }
    
    # Get the ombi users
    try:
        resp = requests.get(f"{request_url}/api/v1/Identity/Users", headers=headers, timeout=5)
        logging.info(f"GET {request_url}/api/v1/Identity/Users - {str(resp.status_code)}")
    except Exception as e:
        logging.error("Error getting ombi users: " + str(e))
        return
    
    # Get the Wizarr Username from the user id
    internal_username = Users.get_by_id(internal_user_id).username
    
    # Create a variable to store the ombi user id
    ombi_user_id = None
    
    # Match Wizarr Username to Ombi Username to get the ombi user id
    for user in resp.json():
        if user["userName"] == internal_username:
            ombi_user_id = user["id"]
            break
    
    # If the ombi user id is not found, return
    if not ombi_user_id:
        logging.info("Ombi user id not found")
        return
    
    # Make the request to delete the user from ombi
    try:
        response = requests.delete(f"{request_url}/api/v1/Identity/{ombi_user_id}", headers=headers, timeout=5)
        logging.info(f"DELETE {request_url}/api/v1/Identity/{ombi_user_id} - {str(response.status_code)}")
        
        return response
    except Exception as e:
        logging.error("Error deleting ombi user: " + str(e))
        return

def overseerr_delete_user(internal_user_id):
    settings = get_settings()
    
    request_url = settings.get("request_url")
    request_api_key = settings.get("request_api_key")
    
    headers = {
        "X-Api-Key": request_api_key,
    }
    
    # Get the overseerr users
    try:
        resp = requests.get(f"{request_url}/api/v1/user?take=2000&skip=0&sort=created", headers=headers, timeout=5)
        logging.info(f"GET {request_url}/api/v1/user - {str(resp.status_code)}")
    except Exception as e:
        logging.error("Error getting overseerr users: " + str(e))
        return
    
    # Get the internal user token from the internal user id
    internal_user_token = Users.get_by_id(internal_user_id).token
        
    # Create a variable to store the overseerr user id
    overseerr_user_id = None
    
    # Take resp and loop through results object to get id of user by finding the user with the same plexId as the internal_user_token
    for user in resp.json()["results"]:
        if int(user["plexId"]) == int(internal_user_token):
            overseerr_user_id = user["id"]
            logging.info(f"Found overseerr user id: {overseerr_user_id}")
            
    # If there are no overseerr users to delete, return
    if not overseerr_user_id:
        logging.error("No overseerr user to delete")
        return
    
    try:
        response = requests.delete(f"{request_url}/api/v1/user/{overseerr_user_id}", headers=headers, timeout=5)
        logging.info(f"DELETE {request_url}/api/v1/user/{overseerr_user_id} - {str(response.status_code)}")
        return response
    except Exception as e:
        logging.error("Error deleting overseerr user: " + str(e))
        return

def jellyseerr_delete_user(internal_user_id):
    settings = get_settings()
    
    request_url = settings.get("request_url")
    request_api_key = settings.get("request_api_key")
    
    headers = {
        "X-Api-Key": request_api_key,
    }
    
    # Get the jellyseerr users
    try:
        resp = requests.get(f"{request_url}/api/v1/user", headers=headers, timeout=5)
        logging.info(f"GET {request_url}/api/v1/user - {str(resp.status_code)}")
    except Exception as e:
        logging.error("Error getting jellyseerr users: " + str(e))
        return
    
    # Create a dictioanry to map internal_user_tokens to usernames
    internal_user_token = Users.get_by_id(internal_user_id).token
    
    # Create a variable to store the jellyseerr user id
    jellyseerr_user_id = None
    
    # Convert the token into jellyseerr user id by looking it up in the jellyseerr users
    for user in resp.json().get("results"):
        if user["jellyfinUserId"] == internal_user_token:
            jellyseerr_user_id = user["id"]
            
    # If there are no jellyseerr users to delete, return
    if not jellyseerr_user_id:
        logging.info("No jellyseerr user to delete")
        return
    
    try:
        response = requests.delete(f"{request_url}/api/v1/user/{jellyseerr_user_id}", headers=headers, timeout=5)
        logging.info(f"DELETE {request_url}/api/v1/user/{jellyseerr_user_id} - {str(response.status_code)}")
        return response
    except Exception as e:
        logging.error("Error deleting jellyseerr user: " + str(e))
        return
