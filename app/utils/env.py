"""Helpers for reading configuration from environment variables."""

import os

_TRUTHY = frozenset({"true", "1", "yes", "on"})


def env_flag(name: str, default: bool = False) -> bool:
    """Read a boolean flag from the environment.

    An unset variable returns ``default``. A set variable is truthy when its
    value is true/1/yes/on, compared case-insensitively with surrounding
    whitespace ignored; any other value is falsy.
    """
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in _TRUTHY
