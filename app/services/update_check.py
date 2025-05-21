import requests, logging, os
from packaging import version

LATEST_URL = "https://raw.githubusercontent.com/Wizarrrr/wizarr/master/.github/latest"

def needs_update() -> bool:
    return False #skip for now
    from app import VERSION
    try:
        latest = requests.get(LATEST_URL, timeout=5).text.strip()
        return version.parse(VERSION) < version.parse(latest)
    except Exception as exc:
        logging.warning("Could not fetch update info: %s", exc)
        return False
