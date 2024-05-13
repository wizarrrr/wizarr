from litestar import Controller, Router, delete, get, post

from app.helpers.invites import Invite, create_invite, invites
from app.models.invite import (
    CreateInviteModel,
    InviteAddModel,
    InviteFilterModel,
    InviteModel,
)
from app.state import State


class InviteController(Controller):
    path = "/{code:str}"

    @delete("/{service_ids:str}")
    async def delete_invite(self, state: State, code: str, service_ids: str) -> None:
        await Invite(state, code).delete(service_ids.split(","))

    @get("/")
    async def invite_get(self, state: State, code: str) -> InviteModel:
        return await Invite(state, code).get()

    @post("/")
    async def invite_add(
        self, state: State, data: list[InviteAddModel], code: str
    ) -> None:
        await Invite(state, code).add(data)


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
