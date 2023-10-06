from requests import get
from packaging.version import parse
from os import path
from json import load

def get_latest_version():
    url = "https://raw.githubusercontent.com/Wizarrrr/wizarr/master/.github/latest"
    response = get(url, timeout=10)
    if response.status_code != 200:
        return None
    return parse(response.content.decode("utf-8")) if response.content else None

def get_latest_beta_version():
    try:
        url = "https://api.github.com/repos/wizarrrr/wizarr/releases"
        response = get(url, timeout=5)
        if response.status_code != 200:
            return None
        releases = response.json()
        latest_beta = [release["tag_name"] for release in releases if release["prerelease"]][0]
        return parse(latest_beta)
    except Exception:
        return None

def get_current_version():
    package = path.abspath(path.join(path.dirname(__file__), "../", "../", "../", "latest"))
    with open(package, "r", encoding="utf-8") as f:
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
    latest_version = is_beta() and get_latest_beta_version() or get_latest_version()
    update = False

    try:
        update = bool(current_version < latest_version)
    except Exception:
        update = False

    return update
