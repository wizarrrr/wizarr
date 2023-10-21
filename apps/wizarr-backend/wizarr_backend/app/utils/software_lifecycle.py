from requests import get
from requests_cache import CachedSession
from packaging.version import parse
from os import path
from json import load
from app.models.database.base import db_dir

from definitions import LATEST_FILE

session = CachedSession(cache_name=path.join(db_dir, "wizarr_cache"), backend="sqlite", expire_after=3600, cache_control=True, stale_if_error=True, allowable_codes=[200])

def get_latest_version():
    try:
        url = "https://api.github.com/repos/wizarrrr/wizarr/releases/latest"
        response = session.get(url, timeout=5)
        if response.status_code != 200:
            return None
        release = response.json()
        latest = release["tag_name"]
        return parse(latest)
    except Exception:
        return None


def get_latest_beta_version():
    try:
        url = "https://api.github.com/repos/wizarrrr/wizarr/releases"
        response = session.get(url, timeout=5)
        if response.status_code != 200:
            return None
        releases = response.json()
        latest_beta = [release["tag_name"] for release in releases if release["prerelease"]][0]
        return parse(latest_beta)
    except Exception:
        return None

def get_current_version():
    with open(LATEST_FILE, "r", encoding="utf-8") as f:
        return parse(f.read())


def is_beta():
    current_version = get_current_version()
    latest_version = get_latest_version()
    beta = False

    try:
        beta = bool(current_version > latest_version)
    except Exception:
        pass

    return beta

def is_stable():
    current_version = get_current_version()
    latest_version = get_latest_version()
    stable = False

    try:
        stable = bool(current_version < latest_version)
    except Exception:
        pass

    return stable

# cache
def need_update():
    current_version = get_current_version()
    latest_version = get_latest_version()
    update = False

    try:
        update = bool(current_version < latest_version)
    except Exception:
        update = False

    return update
