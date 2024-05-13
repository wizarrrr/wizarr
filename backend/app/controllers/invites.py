from litestar import Controller, Router, get, post

from app.helpers.invites import Invite, create_invite, invites
from app.models.invite import (
    CreateInviteModel,
    InviteAddModel,
    InviteFilterModel,
    InviteModel,
)
from app.state import State


class InviteController(Controller):
    path = "/{invite_id:str}"

    @get("/")
    async def invite_get(self, state: State, invite_id: str) -> InviteModel:
        return await Invite(state, invite_id).get()

    @post("/{code:str}")
    async def invite_add(
        self, state: State, data: list[InviteAddModel], invite_id: str, code: str
    ) -> None:
        await Invite(state, invite_id).add(data, code)


@post("/")
async def post_create_invite(state: State, create: CreateInviteModel) -> InviteModel:
    invite, _ = await create_invite(state, create)
    return invite


@get("/")
async def list_invites(
    state: State, data: InviteFilterModel | None = None
) -> list[InviteModel]:
    return await invites(state, data)


routes = Router(
    "/invites", tags=["invites"], route_handlers=[InviteController, post_create_invite]
)

__all__ = ["routes"]
