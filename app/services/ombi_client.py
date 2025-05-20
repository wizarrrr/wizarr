import logging
import requests
from app.models import Settings, User

__all__ = ["run_user_importer", "delete_user"]

def _cfg():
    """Fetch Ombi/Overseerr URL and API key from the DB."""
    url_row = Settings.query.filter_by(key="overseerr_url").first()
    key_row = Settings.query.filter_by(key="ombi_api_key").first()
    return (
        url_row.value if url_row else None,
        key_row.value if key_row else None,
    )

def run_user_importer(name: str):
    url, key = _cfg()
    if not url or not key:
        return

    try:
        resp = requests.post(
            f"{url}/api/v1/Job/{name}UserImporter/",
            headers={"ApiKey": key},
            timeout=5,
        )
        logging.info("Ombi importer %s → %s", name, resp.status_code)
        return resp
    except Exception as exc:
        logging.error("Ombi importer error: %s", exc)

def run_all_importers():
    run_user_importer("jellyfin")   # extend when plex/emby needed

def delete_user(internal_token: str):
    url, key = _cfg()
    if not url or not key:
        return

    # 1. Get Ombi user list
    try:
        users = requests.get(
            f"{url}/api/v1/Identity/Users",
            headers={"ApiKey": key},
            timeout=5,
        ).json()
    except Exception as exc:
        logging.error("Ombi list users failed: %s", exc)
        return

    # 2. Map our internal token → User → Ombi ID
    wiz_user = User.query.filter_by(token=internal_token).first()
    if not wiz_user:
        return

    ombi_id = next(
        (u["id"] for u in users if u.get("userName") == wiz_user.username),
        None
    )

    if ombi_id:
        try:
            resp = requests.delete(
                f"{url}/api/v1/Identity/{ombi_id}",
                headers={"ApiKey": key},
                timeout=5,
            )
            logging.info("Ombi delete user %s → %s", ombi_id, resp.status_code)
            return resp
        except Exception as exc:
            logging.error("Ombi delete user error: %s", exc)
