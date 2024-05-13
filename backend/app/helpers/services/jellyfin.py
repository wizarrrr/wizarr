from app.exceptions import InvalidInviteCode, WeakPassword
from app.helpers.misc import check_password
from app.helpers.services.base import ServiceBase, UserServiceBase


class JellyfinUser(UserServiceBase):
    async def add(self, password: str, code: str) -> None:
        """Invite user to Jellyfin.

        Args:
            password (str): Password to create account with.
            code (str): Invite code.
        """

        try:
            invite = await self._upper.validate_invite(code)
        except InvalidInviteCode:
            raise

        try:
            check_password(password)
        except WeakPassword:
            raise

        created_user = await (
            await self._upper.request(
                "/Users/New", "POST", json={"Name": self._id, "Password": password}
            )
        ).json()

        user_policy: dict[str, bool | str | int | list[str]] = {
            "EnableLiveTvManagement": False,
            "AuthenticationProviderId": "Jellyfin.Server.Implementations.Users.DefaultAuthenticationProvider",
        }

        if invite.folders:
            user_policy["EnableAllFolders"] = False
            user_policy["EnabledFolders"] = invite.folders
        else:
            user_policy["EnableAllFolders"] = True

        if invite.sessions is not None:
            user_policy["MaxActiveSessions"] = invite.sessions

        if invite.hidden is not None:
            user_policy["IsHidden"] = invite.hidden

        if invite.live_tv is not None:
            user_policy["EnableLiveTvAccess"] = invite.live_tv
        else:
            user_policy["EnableLiveTvAccess"] = False

        await self._upper.request(
            f"/Users/{created_user['Id']}/Policy",
            "POST",
            json={**created_user["Policy"], **user_policy},
        )


class Jellyfin(ServiceBase):
    def user(self, id_: str) -> UserServiceBase:
        return JellyfinUser(self._state, self, id_)
