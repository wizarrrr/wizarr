import secrets
from typing import Tuple

from helpers.misc import invite_code_decoded

from app.exceptions import InvalidInviteId, NoPermissionsToService, ServiceNotFound
from app.helpers.services import Service
from app.models.invite import (
    CreateInviteModel,
    InviteAddModel,
    InviteFilterModel,
    InviteModel,
)
from app.state import State


class Invite:
    def __init__(self, state: State, code: str) -> None:
        self._state = state
        self._code = code

    async def get(self) -> InviteModel:
        id_, _ = invite_code_decoded(self._code)

        result = await self._state.mongo.invite.find_one({"_id": id_})
        if not result:
            raise InvalidInviteId()

        return InviteModel(**result)

    async def delete(self, service_ids: list[str]) -> None:
        for service_id in service_ids:
            await (await Service(self._state, service_id).get()).invite(
                self._code
            ).delete()

    async def add(self, service_accounts_to_add: list[InviteAddModel]) -> None:
        invite = await self.get()

        allowed_services = [service for service in invite.service_ids]

        for service in service_accounts_to_add:
            if service.service_id not in allowed_services:
                raise NoPermissionsToService()

            await (await Service(self._state, service.service_id).get()).invite(
                self._code
            ).add(service.name, service.password)


async def invites(
    state: State,
    filter: InviteFilterModel | None = None,
) -> list[InviteModel]:
    search = {}

    if filter:
        if filter.service_ids is not None:
            search["service_ids"] = {"$in": filter.service_ids}

    results = []
    async for result in state.mongo.invite.find(search):
        results.append(InviteModel(**result))

    return results


async def create_invite(
    state: State, invite: CreateInviteModel
) -> Tuple[InviteModel, Invite]:
    if await state.mongo.services.count_documents(
        {"_id": {"$in": invite.service_ids}}
    ) != len(invite.service_ids):
        raise ServiceNotFound()

    _id = secrets.token_urlsafe(6)

    while await state.mongo.invite.count_documents({"_id": _id}) > 0:
        _id = secrets.token_urlsafe(6)

    password = secrets.token_urlsafe(6)

    invite = InviteModel(
        _id=_id,
        password=password,
        **invite.model_dump(),
    )

    await state.mongo.invite.insert_one(invite.model_dump())

    return invite, Invite(state, _id)
