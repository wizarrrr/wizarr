from uuid import uuid4

from exceptions import ServiceNotFound
from helpers.services.base import ServiceBase
from helpers.services.emby import Emby
from helpers.services.jellyfin import Jellyfin
from helpers.services.plex import Plex
from models.services.base import (
    CreateServiceApiModel,
    ServiceApiModel,
    ServiceApiUpdateModel,
)

from app.state import State


def __work_out_service(state: State, service: ServiceApiModel) -> ServiceBase:
    match service.type:
        case "jellyfin":
            return Jellyfin(state, service)
        case "emby":
            return Emby(state, service)
        case _:
            return Plex(state, service)


class Service:
    def __init__(self, state: State, id_: str) -> None:
        self._id = id_
        self._state = state

    @property
    def _where(self) -> dict[str, str]:
        return {"id_": self._id}

    async def get(self) -> ServiceBase:
        result = await self._state.mongo.services.find_one(self._where)
        if not result:
            raise ServiceNotFound()

        return __work_out_service(self._state, ServiceApiModel(**result))

    async def exists(self) -> bool:
        return await self._state.mongo.services.count_documents(self._where) > 0

    async def delete(self) -> None:
        await self._state.mongo.services.delete_one(self._where)

    async def update(self, update: ServiceApiUpdateModel) -> None:
        to_set = update.model_dump(exclude_unset=True)

        await self._state.mongo.services.update_one(self._where, {"$set": to_set})


async def create_service(state: State, service: CreateServiceApiModel) -> ServiceBase:
    """Create a service

    Args:
        state (State)
        service (CreateServiceApiModel)

    Returns:
        ServiceBase
    """

    created_service = ServiceApiModel(_id=str(uuid4()), **service.model_dump())
    await state.mongo.services.insert_one(created_service.model_dump(by_alias=True))

    return __work_out_service(state, created_service)
