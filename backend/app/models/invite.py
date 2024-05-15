from datetime import datetime

from const import SERVICE_TYPES
from pydantic import BaseModel, Field


class CreatePlexInviteModel(BaseModel):
    allow_sync: bool = False
    libraries: list[str] = []


class CreateJellyfinInviteModel(BaseModel):
    libraries: list[str] = []


class CreateEmbyInviteModel(BaseModel):
    libraries: list[str] = []


class CreateInviteModel(BaseModel):
    service_ids: list[str]
    hidden: bool | None = None
    live_tv: bool | None = None
    sessions: int | None = None
    plex: CreatePlexInviteModel | None = None
    jellyfin: CreateJellyfinInviteModel | None = None
    emby: CreateEmbyInviteModel | None = None
    expires: datetime | None = None


class PlexInviteModel(CreatePlexInviteModel):
    user_id: str | None = None


class JellyfinInviteModel(CreateJellyfinInviteModel):
    user_id: str | None = None


class EmbyInviteModel(CreateEmbyInviteModel):
    user_id: str | None = None


class InviteModel(CreateInviteModel):
    id: str = Field(alias="_id")
    password: str
    plex: PlexInviteModel | None = None
    jellyfin: JellyfinInviteModel | None = None
    emby: EmbyInviteModel | None = None


class InviteFilterModel(BaseModel):
    service_ids: list[str] | None = None


class InviteAddModel(BaseModel):
    service_id: str

    name: str | None = None
    password: str
