import logging, requests
from plexapi.server import PlexServer

def check_plex(url: str, token: str) -> bool:
    try:
        PlexServer(url, token=token)
        return True
    except Exception as exc:
        logging.error("Plex check failed: %s", exc, exc_info=True)
        return False

def check_jellyfin(url: str, token: str) -> bool:
    resp = requests.get(f"{url}/Users", headers={"X-Emby-Token": token})
    ok = resp.status_code == 200
    if not ok:
        logging.error("Jellyfin check failed: %s → %s", url, resp.status_code)
    return ok
