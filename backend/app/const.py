from typing import Literal

from argon2 import PasswordHasher

ARGON = PasswordHasher()
SERVICE_TYPES = Literal["jellyfin"] | Literal["plex"] | Literal["emby"]
