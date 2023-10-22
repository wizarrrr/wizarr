from requests import RequestException, get, post, delete
from typing import Optional

from app.models.database.users import Users
from app.models.database.settings import Settings

# ANCHOR - Ombi Get Request
def ombi_get_request(api_path: str, api_url: str, api_key: str):
    """Make a GET request to the Ombi API
    :param api_path: The API path to make the request to
    :param api_key: The API key to use

    :returns: The response from the API
    """

    # If the api_url starts with a /, remove it
    if api_path.startswith("/"):
        api_path = api_path[1:]

    # If the api_url ends with a /, remove it
    if api_path.endswith("/"):
        api_path = api_path[:-1]

    # Add the api_path to the api_url
    api_url = f"{api_url}/{api_path}"

    # Set the headers for Ombi API
    headers = {
        "ApiKey": api_key,
        "Content-Type": "application/json"
    }

    # Get the response from the API
    response = get(api_url, headers=headers, timeout=30)

    # Raise an exception if the request fails with a none 2** status code
    if not response.ok:
        raise RequestException(
            f"Request to {api_url} failed with status code {response.status_code}"
        )

    # Return the response
    return response.json()


# ANCHOR - Ombi Post Request
def ombi_post_request(api_path: str, api_url: str, api_key: str, json: Optional[dict] = None, data: Optional[any] = None):
    """Make a POST request to the Ombi API
    :param api_path: The API path to make the request to
    :param api_key: The API key to use
    :param data: The data to send to the API

    :returns: The response from the API
    """

    # If the api_url starts with a /, remove it
    if api_path.startswith("/"):
        api_path = api_path[1:]

    # If the api_url ends with a /, remove it
    if api_path.endswith("/"):
        api_path = api_path[:-1]

    # Add the api_path to the api_url
    api_url = f"{api_url}/{api_path}"

    # Set the headers for Ombi API
    headers = {
        "ApiKey": api_key,
        "Content-Type": "application/json"
    }

    # Get the response from the API
    response = post(api_url, headers=headers, data=data, json=json, timeout=30)

    # Raise an exception if the request fails with a none 2** status code
    if not response.ok:
        raise RequestException(
            f"Request to {api_url} failed with status code {response.status_code}"
        )

    # Return the response
    return response.json()


# ANCHOR - Ombi Delete Request
def ombi_delete_request(api_path: str, api_url: str, api_key: str):
    """Make a DELETE request to the Ombi API
    :param api_path: The API path to make the request to
    :param api_key: The API key to use

    :returns: The response from the API
    """

    # If the api_url starts with a /, remove it
    if api_path.startswith("/"):
        api_path = api_path[1:]

    # If the api_url ends with a /, remove it
    if api_path.endswith("/"):
        api_path = api_path[:-1]

    # Add the api_path to the api_url
    api_url = f"{api_url}/{api_path}"

    # Set the headers for Ombi API
    headers = {
        "ApiKey": api_key
    }

    # Get the response from the API
    response = delete(api_url, headers=headers, timeout=30)

    # Raise an exception if the request fails with a none 2** status code
    if not response.ok:
        raise RequestException(
            f"Request to {api_url} failed with status code {response.status_code}"
        )

    # Return the response
    return response.json()


# ANCHOR - Ombi Import User
def ombi_import_user(api_url: str, api_key: str):
    """Import a user into Ombi
    :param api_url: The API url to use
    :param api_key: The API key to use
    :param user_token: The Plex user id to import
    """

    # Get the server type from the database
    server_type = Settings.get_or_none(Settings.key == "server_type").value

    # Make the request to the API
    ombi_post_request(f"/api/v1/Job/{server_type}userimporter", api_url, api_key)


# ANCHOR - Ombi Import Users
def ombi_import_users(api_url: str, api_key: str):
    """Import a user into Ombi
    :param api_url: The API url to use
    :param api_key: The API key to use
    :param user_token: List of Plex users id to import
    """

    # Just run omby_import_user
    ombi_import_user(api_url, api_key)


# ANCHOR - Ombi Id from Jellyfin Id
def ombi_id_from_media_server_id(api_url: str, api_key: str, user_token: str):
    """Get a Ombi user id from a Plex user id
    :param api_url: The API url to use
    :param api_key: The API key to use
    :param user_token: The user token to get the Ombi id from
    """

    # PATCH: Get the user username from the database with the user_token
    # There needs to be a fix on Omby's side where they store the Media Server user id
    user = Users.get_or_none(Users.token == user_token)
    username = user.username

    # Get users from Ombi
    response = ombi_get_request("/api/v1/Identity/Users", api_url, api_key)

    # Check if the user is the user we are looking for
    def check_user(user):
        if str(user["userName"]) == str(username):
            return user["id"]

    # Define variable to store the Ombi user id
    ombi_user_id = None

    # Check if the user is in the first page
    for user in response:
        ombi_user_id = check_user(user)
        if ombi_user_id:
            break

    if ombi_user_id is None:
        raise ValueError("Unable to get Ombi user id from Plex user id")

    return ombi_user_id


# ANCHOR - Ombi Delete User
def ombi_delete_user(api_url: str, api_key: str, user_token: str):
    """Delete a user from Ombi
    :param api_url: The API url to use
    :param api_key: The API key to use
    :param user_token: The user token to delete
    """

    # Get the Ombi user id from the Jellyfin user id
    ombi_user_id = ombi_id_from_media_server_id(api_url, api_key, user_token)

    # Delete the user from Ombi
    ombi_delete_request(f"/api/v1/Identity/{ombi_user_id}", api_url, api_key)
