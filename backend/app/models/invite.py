from pydantic import BaseModel, Field


class PlexInviteModel(BaseModel):
    allow_sync: bool = False


class CreateInviteModel(BaseModel):
    folders: list[str] = []
    hidden: bool | None = None
    live_tv: bool | None = None
    sessions: int | None = None
    plex: PlexInviteModel | None = None


class InviteModel(CreateInviteModel):
    id: str = Field(alias="_id")
    password: str

    # Will be none if user hasn't linked their account yet.
    external_service_user_id: str | None = None
