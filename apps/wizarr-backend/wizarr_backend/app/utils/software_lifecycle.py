from requests import get
from requests_cache import CachedSession
from packaging.version import parse
from os import path
from json import load
from definitions import LATEST_FILE, DATABASE_DIR

session = CachedSession(cache_name=path.join(DATABASE_DIR, "wizarr_cache"), backend="sqlite", expire_after=3600, cache_control=True, stale_if_error=True, allowable_codes=[200])

def get_latest_version():
    try:
        url = "https://api.github.com/repos/wizarrrr/wizarr/releases/latest"
        response = session.get(url, timeout=5)
        if response.status_code != 200:
            return None
        release = response.json()
        latest = release["tag_name"]
        return str(latest)
    except Exception:
        return None

def get_latest_beta_version():
    try:
        url = "https://api.github.com/repos/wizarrrr/wizarr/releases"
        response = session.get(url, timeout=5)
        if response.status_code != 200:
            return None
        releases = response.json()
        latest_beta = str([release["tag_name"] for release in releases if release["prerelease"] and "beta" in release["tag_name"]][0])

        # TEMPORARY FIX: Remove -v3 from the version
        latest_beta = latest_beta.replace("-v3", "")

        return parse(latest_beta)
    except Exception:
        return None

def get_current_version():
    with open(LATEST_FILE, "r", encoding="utf-8") as f:
        current_version = str(f.read())

        # TEMPORARY FIX: Remove -v3 from the version
        current_version = current_version.replace("-v3", "")

        return parse(current_version)

def compare_versions(version1, version2):
    return parse(str(version1)) > parse(str(version2))

def is_beta():
    return "beta" in str(get_current_version())

def is_latest():
    return compare_versions(get_current_version(), is_beta() and get_latest_beta_version() or get_latest_version())

def is_stable():
    return not is_beta()

def need_update():
    return not is_latest()
