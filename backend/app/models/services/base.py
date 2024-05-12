from typing import Literal

from pydantic import BaseModel


class ServiceApiModel(BaseModel):
    name: Literal["jellyfin"] | Literal["plex"] | Literal["emby"]
    key: str
    url: str
