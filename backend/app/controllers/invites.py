from helpers.invites import Invite
from litestar import Controller, Router, post

from app.models.invite import InviteAddModel
from app.state import State


class InviteController(Controller):
    path = "/{invite_id:str}"

    @post("/{code:str}")
    async def invite_add(
        self, state: State, data: list[InviteAddModel], invite_id: str, code: str
    ) -> None:
        await Invite(state, invite_id).add(data, code)


routes = Router("/invites", tags=["invites"], route_handlers=[InviteController])

__all__ = ["routes"]
