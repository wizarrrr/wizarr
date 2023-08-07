from logging import info

from packaging.version import parse
from requests import get


def need_update(version: str):
    try:
        r = get(url="https://raw.githubusercontent.com/Wizarrrr/wizarr/master/.github/latest")
        data = r.content.decode("utf-8")
        return parse(version) < parse(data)
    except Exception as e:
        info(f"Error checking for updates: {e}")
        return False