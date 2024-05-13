from datetime import datetime, timezone

from app.const import ARGON
from app.exceptions import AccountNotFound, EmailTaken, WeakPassword
from app.helpers.misc import check_password
from app.models.account import AccountModel, AccountUpdateModel
from app.state import State


class Account:
    def __init__(self, state: State, email: str) -> None:
        self._state = state
        self._email = email

    @property
    def _where(self) -> dict[str, str]:
        return {"email": self._email}

    async def get(self) -> AccountModel:
        result = await self._state.mongo.account.find_one(self._where)
        if not result:
            raise AccountNotFound()

        return AccountModel(**result)

    async def exists(self) -> bool:
        return await self._state.mongo.account.count_documents(self._where) > 0

    async def delete(self) -> None:
        await self._state.mongo.account.delete_one(self._where)

    async def update(self, update: AccountUpdateModel) -> None:
        to_set = update.model_dump(exclude_unset=True)

        if "email" in to_set and await Account(self._state, to_set["email"]).exists():
            raise EmailTaken()

        await self._state.mongo.update_one(self._where, {"$set": to_set})

    async def create(self, password: str) -> AccountModel:
        if await self.exists():
            raise EmailTaken()

        try:
            check_password(password)
        except WeakPassword:
            raise

        password_hash = ARGON.hash(password)

        created_account = AccountModel(
            password_hash=password_hash,
            email=self._email,
            created=datetime.now(tz=timezone.utc),
        )

        await self._state.mongo.account.insert_one(created_account.model_dump())

        return created_account
