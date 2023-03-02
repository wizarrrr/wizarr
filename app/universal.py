from app.plex import *
from app.jellyfin import *
from app.ombi import *


def global_delete_user(user):
    server_type = Settings.get(Settings.key == "server_type").value
    if server_type == "plex":
        try:
            plex_delete_user(user)
        except Exception as e:
            if "429" in str(e):
                logging.error("Too many requests to Plex API")
            else:
                logging.error("Unable to delete user: " + str(e))
    elif server_type == "jellyfin":
        jf_delete_user(user)
    Users.delete().where(Users.id == user).execute()
    ombi_delete_user(user)


def global_get_users():
    server_type = Settings.get(Settings.key == "server_type").value
    if server_type == "plex":
        try:
            users = plex_get_users()
            return users
        except Exception as e:
            if "429" in str(e):
                logging.error("Too many requests to Plex API")
            else:
                logging.error("Unable to get users: " + str(e))
    elif server_type == "jellyfin":
        try:
            users = jf_get_users()
            return users
        except Exception as e:
            if "429" in str(e):
                logging.error("Too many requests to Jellyfin API")
            else:
                logging.error("Unable to get users: " + str(e))