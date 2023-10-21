from requests import RequestException, get, post, delete
from typing import Optional
from app.models.database.users import Users

# ANCHOR - Overseerr Get Request
def overseerr_get_request(api_path: str, api_url: str, api_key: str):
    """Make a GET request to the Overseerr API
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

    # Set the headers for Overseerr API
    headers = {
        "X-Api-Key": api_key,
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


# ANCHOR - Overseerr Post Request
def overseerr_post_request(api_path: str, api_url: str, api_key: str, json: Optional[dict] = None, data: Optional[any] = None):
    """Make a POST request to the Overseerr API
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

    # Set the headers for Overseerr API
    headers = {
        "X-Api-Key": api_key,
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


# ANCHOR - Overseerr Delete Request
def overseerr_delete_request(api_path: str, api_url: str, api_key: str):
    """Make a DELETE request to the Overseerr API
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

    # Set the headers for Overseerr API
    headers = {
        "X-Api-Key": api_key
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


# ANCHOR - Overseerr Import User
def overseerr_import_user(api_url: str, api_key: str, user_token: str):
    """Import a user into Overseerr
    :param api_url: The API url to use
    :param api_key: The API key to use
    :param user_token: The Plex user id to import
    """

    # Set the data to send to the API
    data = {
        "plexIds": [str(user_token)]
    }

    # Make the request to the API
    overseerr_post_request("/api/v1/user/import-from-plex", api_url, api_key, json=data)


# ANCHOR - Overseerr Import Users
def overseerr_import_users(api_url: str, api_key: str, user_token: list[str]):
    """Import a user into Overseerr
    :param api_url: The API url to use
    :param api_key: The API key to use
    :param user_token: List of Plex users id to import
    """

    # Set the data to send to the API
    data = {
        "plexIds": [str(token) for token in user_token]
    }

    # Make the request to the API
    overseerr_post_request("/api/v1/user/import-from-plex", api_url, api_key, json=data)


# ANCHOR - Overseerr Id from Jellyfin Id
def overseerr_id_from_plex_id(api_url: str, api_key: str, user_token: str):
    """Get a Overseerr user id from a Plex user id
    :param api_url: The API url to use
    :param api_key: The API key to use
    :param user_token: The user token to get the Overseerr id from
    """

    # Get users from Overseerr using pagination
    def get_users(page: int = 1, pageSize: int = 10):
        return overseerr_get_request("/api/v1/user?take={}&skip={}".format(pageSize, (page - 1) * pageSize), api_url, api_key)

    # Check if the user is the user we are looking for
    def check_user(user):
        if str(user["plexId"]) == str(user_token):
            return user["id"]

    # Define variable to store the Overseerr user id
    overseerr_user_id = None

    # Get the first page of users
    response = get_users()

    # Check if the user is in the first page
    for user in response["results"]:
        overseerr_user_id = check_user(user)
        if overseerr_user_id:
            break

    # If the user is not in the first page, get the rest of the pages
    if not overseerr_user_id:
        for page in range(2, response["pageInfo"]["pages"] + 1):
            response = get_users(page)
            for user in response["results"]:
                overseerr_user_id = check_user(user)
                if overseerr_user_id:
                    break

    if overseerr_user_id is None:
        raise ValueError("Unable to get Overseerr user id from Plex user id")

    return overseerr_user_id


# ANCHOR - Overseerr Delete User
def overseerr_delete_user(api_url: str, api_key: str, user_token: str):
    """Delete a user from Overseerr
    :param api_url: The API url to use
    :param api_key: The API key to use
    :param user_token: The user token to delete
    """

    # Get the Overseerr user id from the Jellyfin user id
    overseerr_user_id = overseerr_id_from_plex_id(api_url, api_key, user_token)

    # Delete the user from Overseerr
    overseerr_delete_request(f"/api/v1/user/{overseerr_user_id}", api_url, api_key)
