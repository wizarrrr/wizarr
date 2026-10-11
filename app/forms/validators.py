"""
Shared form validation constants and filters.
"""

from typing import Any

USERNAME_PATTERN = r"^[\w'.-]+$"
USERNAME_MIN_LENGTH = 3
USERNAME_MAX_LENGTH = 15
USERNAME_LENGTH_MESSAGE = "Username must be 3 to 15 characters."
USERNAME_ALLOWED_CHARS_MESSAGE = (
    "Username can contain letters, numbers, dashes (-), underscores (_), "
    "apostrophes ('), and periods (.)."
)


def strip_filter(value: Any):
    """Trim leading/trailing whitespace from string inputs before validation."""
    if isinstance(value, str):
        return value.strip()
    return value
