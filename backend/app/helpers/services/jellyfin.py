from app.exceptions import InvalidInviteCode, WeakPassword
from app.helpers.misc import check_password
from app.helpers.services.base import ServiceBase, ServiceInviteBase


class JellyfinInvite(ServiceInviteBase):
    async def add(self, name: str, password: str) -> None:
        """Invite user to Jellyfin.

        Args:
            name (str): Name of jellyfin user to create.
            password (str): Password to create account with.
        """

        # Run shared invite logic.
        invite = await super().add(name, password)

        created_user = await (
            await self._upper.request(
                "/Users/New", "POST", json={"Name": name, "Password": password}
            )
        ).json()

        user_policy: dict[str, bool | str | int | list[str]] = {
            "EnableLiveTvManagement": False,
            "AuthenticationProviderId": "Jellyfin.Server.Implementations.Users.DefaultAuthenticationProvider",
        }

        if invite.jellyfin and invite.jellyfin.libraries:
            user_policy["EnableAllFolders"] = False
            user_policy["EnabledFolders"] = invite.jellyfin.libraries
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

        await self._upper._state.mongo.invite.update_one(
            {"_id": invite.id},
            {"$set": {"external_service_user_id": created_user["Id"]}},
        )

    async def delete(self) -> None:
        invite = await self.get()

        if invite.external_service_user_id:
            await self._upper.request(
                f"/Users/{invite.external_service_user_id}", "DELETE"
            )

        await super().delete()


class Jellyfin(ServiceBase):
    def invite(self, code: str) -> ServiceInviteBase:
        return JellyfinInvite(self._state, self, code)
