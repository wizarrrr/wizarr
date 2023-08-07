from requests import get
from packaging.version import parse
from os import path
from json import load

def get_latest_version():
    url = "https://raw.githubusercontent.com/Wizarrrr/wizarr/master/.github/latest"
    response = get(url, timeout=10)
    return parse(response.content.decode("utf-8"))

def get_current_version():
    package = path.abspath(path.join(path.dirname(__file__), "../", "../", "package.json"))
    with open(package, "r", encoding="utf-8") as f:
        return parse(load(f)["version"])


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

def need_update():
    current_version = get_current_version()
    latest_version = get_latest_version()
    update = False

    try:
        update = bool(current_version < latest_version)
    except Exception:
        pass

    return update
