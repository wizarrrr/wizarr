"""Custom Plex API methods that extend or replace PlexAPI library functionality.

This module contains direct HTTP calls to Plex APIs that are not properly supported
by the python-plexapi library, or where the library's implementation is outdated.
"""

import logging


def accept_invite_v2(account, user: str):
    """Accept a Plex server invitation using the v2 shared_servers API.

    This replaces the broken acceptInvite() method in PlexAPI which uses
    an outdated API endpoint.

    Args:
        account: MyPlexAccount instance
        user: Username, email, or friendly name of the inviting user

    Returns:
        Response object from the API call

    Raises:
        ValueError: If no pending invite is found or invite structure is invalid
    """
    base = "https://clients.plex.tv"

    # Build default Plex client headers
    params = {
        "X-Plex-Product": "Wizarr",
        "X-Plex-Version": "1.0",
        "X-Plex-Client-Identifier": account.uuid,
        "X-Plex-Platform": "Web",
        "X-Plex-Platform-Version": "1.0",
        "X-Plex-Device": "Web",
        "X-Plex-Device-Name": "Wizarr",
        "X-Plex-Model": "bundled",
        "X-Plex-Features": "external-media,indirect-media,hub-style-list",
        "X-Plex-Language": "en",
    }

    params["X-Plex-Token"] = account.authToken
    hdrs = {"Accept": "application/json"}

    # Get pending invites
    url_list = f"{base}/api/v2/shared_servers/invites/received/pending"
    resp = account._session.get(url_list, params=params, headers=hdrs)
    resp.raise_for_status()
    invites = resp.json()

    # Find matching invite
    def _matches(inv):
        o = inv.get("owner", {})
        return user in (
            o.get("username"),
            o.get("email"),
            o.get("title"),
            o.get("friendlyName"),
        )

    try:
        inv = next(i for i in invites if _matches(i))
    except StopIteration as exc:
        raise ValueError(f"No pending invite from '{user}' found") from exc

    shared_servers = inv.get("sharedServers")
    if not shared_servers:
        raise ValueError("Invite structure missing 'sharedServers' list")

    invite_id = shared_servers[0]["id"]

    # Accept the invite
    url_accept = f"{base}/api/v2/shared_servers/{invite_id}/accept"
    resp = account._session.post(url_accept, params=params, headers=hdrs)
    resp.raise_for_status()
    return resp


def update_shared_server(
    account,
    shared_server_id: int,
    settings: dict,
    section_ids: list[int],
) -> bool:
    """Update a shared server's permissions and library access.

    This uses the modern /shared_servers/ API that Plex Web uses, which is more
    reliable than the PlexAPI library's updateFriend() method.

    Args:
        account: MyPlexAccount instance
        shared_server_id: The shared server ID (not the same as sharing_id)
        settings: Dict with permission flags:
            - allowSync: bool
            - allowChannels: bool
            - allowCameraUpload: bool
            - filterMovies: str (usually "")
            - filterMusic: str (usually "")
            - filterPhotos: str | None
            - filterTelevision: str (usually "")
            - filterAll: str | None
            - allowSubtitleAdmin: bool (usually False)
            - allowTuners: int (usually 0)
        section_ids: List of numeric library section IDs to grant access to

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        base = "https://clients.plex.tv"
        url = f"{base}/api/v2/shared_servers/{shared_server_id}"

        # Build request payload
        payload = {
            "settings": settings,
            "librarySectionIds": section_ids,
        }

        # Build headers with Plex client info
        params = {
            "X-Plex-Product": "Wizarr",
            "X-Plex-Version": "1.0",
            "X-Plex-Client-Identifier": account.uuid,
            "X-Plex-Token": account.authToken,
            "X-Plex-Platform": "Web",
            "X-Plex-Platform-Version": "1.0",
            "X-Plex-Features": "external-media,indirect-media,hub-style-list",
            "X-Plex-Language": "en",
        }

        headers = {"Accept": "application/json", "Content-Type": "application/json"}

        logging.info(f"Updating shared_server {shared_server_id}")
        logging.info(f"Sending payload: {payload}")

        resp = account._session.post(url, params=params, headers=headers, json=payload)
        resp.raise_for_status()

        logging.info(f"Response status: {resp.status_code}")
        logging.info(f"Response body: {resp.text[:500] if resp.text else 'empty'}")

        return True
    except Exception as e:
        logging.error(f"Failed to update shared_server {shared_server_id}: {e}")
        return False
