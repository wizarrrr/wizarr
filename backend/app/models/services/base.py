from typing import Literal

from pydantic import BaseModel, Field, HttpUrl


class CreateServiceApiModel(BaseModel):
    alias: str | None = Field(None, max_length=64)
    type: Literal["jellyfin"] | Literal["plex"] | Literal["emby"]
    key: str = Field(max_length=128)
    url: HttpUrl


class ServiceApiModel(CreateServiceApiModel):
    id: str = Field(alias="_id", description="Unique ID for service", min_length=3)


class ServiceApiUpdateModel(BaseModel):
    type: str | None = None
    alias: str | None = None
    key: str | None = None
    url: str | None = None
