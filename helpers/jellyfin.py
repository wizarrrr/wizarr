from pydantic import HttpUrl
from requests import RequestException, get, post
from .settings import get_settings
from .invitation import get_invitation
from .libraries import get_libraries_id

# INDEX OF FUNCTIONS
# - Jellyfin Scan Libraries
# - Jellyfin Get Request
# - Jellyfin Post Request
# - Jellyfin Invite User


# ANCHOR - Jellyfin Scan Libraries
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


# ANCHOR - Jellyfin Get Request
def get_jellyfin(api_path: str, server_api_key: str = None, server_url: HttpUrl = None):
    # Get required settings
    if server_api_key is None or server_url is None:
        settings = get_settings(["server_api_key", "server_url"])
        server_url = server_url or settings.get("server_url", None)
        server_api_key = server_api_key or settings.get("server_api_key", None)
    
    # Add api_path to Jellyfin URL
    api_url = str(server_url) + api_path
    
    # Get data from Jellyfin
    headers = { "X-Emby-Token": server_api_key }
    response = get(url=api_url, headers=headers, timeout=30)
    
    # Raise exception if Jellyfin API returns non-200 status code
    if response.status_code != 200:
        raise RequestException(f"Jellyfin API returned {response.status_code} status code.")
    
    return response.json()


# ANCHOR - Jellyfin Post Request
def post_jellyfin(api_path: str, server_api_key: str = None, server_url: HttpUrl = None, data: dict = None):
    # Get required settings
    if server_api_key is None or server_url is None:
        settings = get_settings(["server_api_key", "server_url"])
        server_url = server_url or settings.get("server_url", None)
        server_api_key = server_api_key or settings.get("server_api_key", None)
    
    # Add api_path to Jellyfin URL
    api_url = str(server_url) + api_path
    
    # Get data from Jellyfin
    headers = { "X-Emby-Token": server_api_key }
    response = post(url=api_url, headers=headers, data=data, timeout=30)
    
    # Raise exception if Jellyfin API returns non-200 status code
    if response.status_code != 200:
        raise RequestException(f"Jellyfin API returned {response.status_code} status code.")
    
    return response.json()


# ANCHOR - Jellyfin Invite User
def invite_jellyfin_user(username: str, password: str, code: str, email: str):
    # Validate user input
    if not username or not password or not code or not email:
        raise ValueError("Missing required user input.")
    
    # Get Invitation from Database
    invitation = get_invitation(code=code)
    sections = get_libraries_id() if invitation.specific_libraries is None else invitation.specific_libraries.split(",")
    
    # Create user object
    new_user = {
        "Name": str(username),
        "Password": str(password)
    }
    
    # Create policy object
    new_policy = {
        "EnableAllFolders": False,
        "EnabledFolders": sections
    }
    
    # Create user in Jellyfin
    response = post_jellyfin(api_path="/Users/New", data=new_user)
    
    # Get user ID from Jellyfin response
    response_json = response.json()
    user_id = response_json["Id"]
    
