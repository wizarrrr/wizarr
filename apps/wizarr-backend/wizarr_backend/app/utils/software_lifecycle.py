from requests import get
from requests_cache import CachedSession
from packaging.version import parse
from os import path
from json import load
from definitions import LATEST_FILE, DATABASE_DIR
from re import search

session = CachedSession(cache_name=path.join(DATABASE_DIR, "wizarr_cache"), backend="sqlite", expire_after=3600, cache_control=True, stale_if_error=True, allowable_codes=[200])

def compare_versions(version1, version2):
    return parse(str(version1)) > parse(str(version2))

def get_latest_version():
    try:
        url = "https://api.github.com/repos/wizarrrr/wizarr/tags"
        response = session.get(url, timeout=5)
        if response.status_code != 200: return None
        latest = None
        for tag in response.json():
            if latest is None or compare_versions(tag["name"], latest):
                if "beta" not in tag["name"]:
                    latest = tag["name"]
        return parse(str(latest))
    except Exception:
        return None

def get_latest_beta_version():
    try:
        url = "https://api.github.com/repos/wizarrrr/wizarr/tags"
        response = session.get(url, timeout=5)
        if response.status_code != 200: return None
        latest_beta = None
        for tag in response.json():
            if latest_beta is None or compare_versions(tag["name"], latest_beta):
                if "beta" in tag["name"]:
                    latest_beta = tag["name"]
        return parse(str(latest_beta))
    except Exception:
        return None

def get_current_version():
    with open(LATEST_FILE, "r", encoding="utf-8") as f:
        current_version = str(f.read())
        return parse(current_version)

def is_beta():
    return search(r"\d\.\d\.\d\w\d", str(get_current_version())) is not None

def is_latest():
    if str(get_current_version()) == str(is_beta() and get_latest_beta_version() or get_latest_version()):
        return True
    return compare_versions(get_current_version(), is_beta() and get_latest_beta_version() or get_latest_version())

def is_stable():
    return not is_beta()

def need_update():
    return not is_latest()
