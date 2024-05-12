from typing import Literal

from aiohttp.client import ClientResponse
from exceptions import ServiceIdTaken
from models.services.base import ServiceApiModel, ServiceApiUpdateModel

from app.state import State


class UserService:
    def __init__(self, state: State, id_: str) -> None:
        self._state = state
        self._id = id_

    async def invite(self) -> None: ...

    async def delete(self) -> None: ...

    async def get(self) -> None: ...


class Service:
    def __init__(self, state: State, service: ServiceApiModel) -> None:
        self._state = state
        self._service = service

    @property
    def _where(self) -> dict[str, str]:
        return {"id_": self._service.id}

    async def exists(self) -> bool:
        return await self._state.mongo.services.count_documents(self._where) > 0

    async def delete(self) -> None:
        await self._state.mongo.services.delete_one(self._where)

    async def update(self, update: ServiceApiUpdateModel) -> None:
        to_set = update.model_dump(exclude_unset=True)

        await self._state.mongo.services.update_one(self._where, {"$set": to_set})

    async def create(self) -> None:
        if await self.exists():
            raise ServiceIdTaken()

        await self._state.mongo.services.insert_one(
            self._service.model_dump(by_alias=True)
        )

    async def request(
        self,
        path: str,
        method: Literal["POST"] | Literal["GET"] | Literal["DELETE"] | Literal["PATCH"],
        **kwargs,
    ) -> ClientResponse:
        url = str(self._service.url)
        if url.endswith("/"):
            url = url.removesuffix("/")

        if "headers" not in kwargs:
            kwargs["headers"] = {}

        kwargs["headers"][
            "X-Emby-Token" if self._service.name != "plex" else "X-Plex-Token"
        ] = self._service.key

        return await self._state.aiohttp.request(
            method=method, url=f"{self._service.url}/{path}", **kwargs
        )

    async def policy(self) -> None: ...

    async def scan(self) -> None: ...

    async def sync(self) -> None: ...

    async def invite(self) -> None: ...

    async def users(self) -> None: ...

    async def user(self, id_: str) -> UserService: ...
