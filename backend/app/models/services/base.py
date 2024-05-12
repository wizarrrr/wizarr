from typing import Literal

from pydantic import BaseModel, Field, HttpUrl


class ServiceApiModel(BaseModel):
    id: str = Field(alias="_id", description="Unique ID for service", min_length=3)
    name: Literal["jellyfin"] | Literal["plex"] | Literal["emby"]
    key: str = Field(max_length=128)
    url: HttpUrl


class ServiceApiUpdateModel(BaseModel):
    name: str | None = None
    key: str | None = None
    url: str | None = None
