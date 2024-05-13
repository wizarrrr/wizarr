import secrets
from typing import Literal, Tuple

from aiohttp.client import ClientResponse
from argon2.exceptions import VerificationError

from app.const import ARGON
from app.exceptions import InvalidInviteCode, WeakPassword
from app.helpers.misc import check_password
from app.models.invite import CreateInviteModel, InviteModel
from app.models.services.base import ServiceApiModel
from app.state import State


class ServiceInviteBase:
    def __init__(self, state: State, upper: "ServiceBase", code: str) -> None:
        self._state = state
        self._upper = upper
        self._code = code

    @property
    def code_decoded(self) -> Tuple[str, str]:
        try:
            _id, password = self._code.split(":")
        except ValueError:
            raise InvalidInviteCode()

        return _id, password

    async def add(self, password: str) -> InviteModel:
        try:
            invite = await self.validate()
        except InvalidInviteCode:
            raise

        try:
            check_password(password)
        except WeakPassword:
            raise

        return invite

    async def delete(self) -> None:
        id_, _ = self.code_decoded

        await self._state.mongo.delete_one({"_id": id_})

    async def get(self) -> InviteModel:
        id_, _ = self.code_decoded

        result = await self._state.mongo.invite.find_one({"_id", id_})
        if not result:
            raise InvalidInviteCode()

        return InviteModel(**result)

    async def validate(self) -> InviteModel:
        _, password = self.code_decoded

        invite = await self.get()

        try:
            # Timing attacks
            ARGON.verify(ARGON.hash(password), password)
        except VerificationError:
            raise InvalidInviteCode()

        return invite


class ServiceBase:
    def __init__(self, state: State, service: ServiceApiModel) -> None:
        self._state = state
        self._service = service

    @property
    def details(self) -> ServiceApiModel:
        return self._service

    def invite(self, code: str) -> ServiceInviteBase: ...

    async def create_invite(self, invite: CreateInviteModel) -> InviteModel:
        _id = secrets.token_urlsafe(6)

        while await self._state.mongo.invite.count_documents({"_id": _id}) > 0:
            _id = secrets.token_urlsafe(6)

        password = secrets.token_urlsafe(6)

        invite = InviteModel(_id=_id, password=password, **invite.model_dump())

        await self._state.mongo.invite.insert_one(invite.model_dump())

        return invite

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
            "X-Emby-Token" if self._service.type != "plex" else "X-Plex-Token"
        ] = self._service.key

        resp = await self._state.aiohttp.request(
            method=method, url=f"{self._service.url}/{path}", **kwargs
        )

        resp.raise_for_status()

        return resp

    async def policy(self) -> None: ...

    async def scan(self) -> None: ...

    async def sync(self) -> None: ...

    async def users(self) -> None: ...

    def user(self, id_: str) -> None: ...
