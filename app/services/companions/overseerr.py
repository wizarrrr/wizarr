"""
Overseerr/Jellyseerr companion client implementation.
"""

import logging
import time

import requests

from app.models import Connection

from .base import CompanionClient

# Overseerr checks the user can reach the media server before it will accept
# them, and plex.tv does not necessarily publish a brand new share the instant it
# is created. How long that takes has not been measured here, so retry over a few
# minutes rather than assuming it is immediate. This runs off the request thread,
# so a long tail costs the invited user nothing.
_PROVISION_BACKOFF_SECONDS = (10, 30, 60, 120, 240)


def _open_session(
    base_url: str,
) -> tuple[requests.Session, dict[str, str], requests.Response | None]:
    """Open a session carrying Overseerr's CSRF cookie, if it wants one.

    Overseerr can be configured to reject state-changing requests that do not
    echo its XSRF cookie back as a header, and that applies to API callers, not
    just browsers - without it every POST comes back 403 "invalid csrf token"
    no matter how valid the payload is. A GET first hands us the cookie.
    Instances with the protection off simply never set one, and we send no
    header.

    Returns:
        The session to post with, the headers it needs, and the status
        response, which the caller may want for its own reasons
    """
    session = requests.Session()
    headers: dict[str, str] = {}

    try:
        resp = session.get(f"{base_url}/api/v1/status", timeout=10)
    except Exception as exc:
        # Not fatal on its own: let the POST report the real failure.
        logging.debug("Could not prime Overseerr CSRF cookie: %s", exc)
        return session, headers, None

    token = session.cookies.get("XSRF-TOKEN")
    if token:
        headers["X-XSRF-TOKEN"] = token

    return session, headers, resp


class OverseerrClient(CompanionClient):
    """Client for integrating with Overseerr/Jellyseerr.

    Informational by default: they import nobody in the background and
    creates an account on first sign-in. With account creation turned on, an
    invite provisions that account up front instead.
    """

    @property
    def requires_api_call(self) -> bool:
        return False

    @property
    def display_name(self) -> str:
        return "Overseerr/Jellyseerr"

    def invite_user(
        self,
        username: str,  # noqa: ARG002
        email: str,  # noqa: ARG002
        connection: Connection,  # noqa: ARG002
        password: str = "",  # noqa: ARG002
    ) -> dict[str, str]:
        """
        Overseerr connections are info-only, no actual API calls needed.

        Args:
            username: Username to invite (unused - info-only)
            email: Email address (unused - info-only)
            connection: Connection object with URL and API key (unused - info-only)
            password: Password for the user (unused - info-only)

        Returns:
            Dict with 'status' and 'message' keys
        """
        return {
            "status": "info_only",
            "message": "Overseerr auto-imports users automatically",
        }

    def delete_user(self, username: str, connection: Connection) -> dict[str, str]:  # noqa: ARG002
        """
        Overseerr connections are info-only, no deletion needed.

        Args:
            username: Username to delete (unused - info-only)
            connection: Connection object with URL and API key (unused - info-only)

        Returns:
            Dict with 'status' and 'message' keys
        """
        return {
            "status": "info_only",
            "message": "Overseerr users managed automatically",
        }

    def test_connection(self, connection: Connection) -> dict[str, str]:
        """
        Check everything account creation depends on, without credentials.

        Every prerequisite is readable anonymously, so this exercises the real
        provisioning path rather than approximating it: the same session helper,
        the same CSRF handshake, and the setting Overseerr refuses the sign-in
        without. The point is to surface a broken invite here rather than
        silently, minutes later, in a background thread the admin never sees.

        Args:
            connection: Connection object with URL and API key

        Returns:
            Dict with 'status' and 'message' keys
        """
        name = self.display_name

        if not connection.url:
            return {
                "status": "info_only",
                "message": (
                    "No Service URL set, so this connection is informational "
                    "and Wizarr makes no calls to " + name + "."
                ),
            }

        base_url = connection.url.rstrip("/")

        try:
            session, headers, status = _open_session(base_url)
        except Exception as exc:
            return {"status": "error", "message": f"Could not reach {base_url}: {exc}"}

        if status is None:
            return {
                "status": "error",
                "message": f"Could not reach {base_url}. Check the URL and that {name} is running.",
            }
        if not status.ok:
            return {
                "status": "error",
                "message": f"{base_url}/api/v1/status returned HTTP {status.status_code}.",
            }

        try:
            version = str(status.json()["version"])
        except Exception:
            return {
                "status": "error",
                "message": (
                    f"{base_url} answered, but not with {name}'s API. Check the URL "
                    f"points at {name} itself rather than a login page or proxy error."
                ),
            }

        if not self._csrf_handshake_works(session, headers, base_url):
            return {
                "status": "error",
                "message": (
                    f"Reached {name} {version}, but it rejected a test request as "
                    "CSRF-invalid. Its CSRF cookies are Secure, so an http:// URL "
                    "can never satisfy them. Use https here, or turn off CSRF "
                    f"protection in {name}."
                ),
            }

        new_plex_login = self._new_plex_login_enabled(session, base_url)
        if new_plex_login is False:
            return {
                "status": "error",
                "message": (
                    f"Reached {name} {version}, but 'Enable New Plex Sign-In' is off "
                    "under its Settings → Users, so it will refuse to create the "
                    "account. Turn it on, or leave account creation off here."
                ),
            }

        if not connection.provision_plex_users:
            return {
                "status": "info_only",
                "message": (
                    f"Reached {name} {version}. Account creation is off, so this "
                    "connection is informational and invited users will sign in "
                    f"to {name} themselves."
                ),
            }

        if new_plex_login is None:
            return {
                "status": "success",
                "message": (
                    f"Reached {name} {version} and the CSRF handshake worked. Could "
                    "not read its settings to confirm 'Enable New Plex Sign-In' is "
                    "on, which account creation needs."
                ),
            }

        return {
            "status": "success",
            "message": (
                f"Reached {name} {version}. CSRF handshake worked and 'Enable New "
                "Plex Sign-In' is on, so account creation should succeed."
            ),
        }

    @staticmethod
    def _csrf_handshake_works(
        session: requests.Session, headers: dict[str, str], base_url: str
    ) -> bool:
        """Prove a POST survives CSRF, without provisioning anyone.

        Logout is the one state-changing route that clears the CSRF middleware
        before it needs credentials, so it answers the only question worth
        asking here. Sending no session cookie, it has nothing to log out and
        returns 401, which is the pass condition: the request got past CSRF.
        Posting a throwaway token to the real sign-in route would test the same
        thing while making Overseerr call plex.tv and log a failure.

        Returns:
            Whether a POST gets past Overseerr's CSRF check
        """
        try:
            resp = session.post(
                f"{base_url}/api/v1/auth/logout", headers=headers, timeout=10
            )
        except Exception as exc:
            # Reachability is already established, so this is not the check
            # failing so much as the check being unable to run. Do not block on
            # it: provisioning reports its own CSRF failures with the same text.
            logging.debug("Overseerr CSRF probe could not run: %s", exc)
            return True

        body = (resp.text or "").lower()
        return not (resp.status_code == 403 and "csrf" in body)

    @staticmethod
    def _new_plex_login_enabled(
        session: requests.Session, base_url: str
    ) -> bool | None:
        """Read the setting Overseerr refuses a new Plex sign-in without.

        Returns:
            Whether new Plex sign-in is enabled, or None if it could not be read
        """
        try:
            resp = session.get(f"{base_url}/api/v1/settings/public", timeout=10)
            if not resp.ok:
                return None
            value = resp.json().get("newPlexLogin")
        except Exception as exc:
            logging.debug("Could not read Overseerr public settings: %s", exc)
            return None

        return bool(value) if isinstance(value, bool) else None

    def provision_plex_user(
        self, auth_token: str, connection: Connection
    ) -> dict[str, str]:
        """
        Create the Overseerr account for a freshly invited Plex user.

        Overseerr does not import Plex users in the background; it creates them
        the first time they sign in. That leaves an invited user having to go and
        log in by hand before anything knows who they are, and before watchlist
        syncing has a token to work with. Posting their Plex token to the same
        endpoint the login page uses does exactly what that visit would have.

        Needs no API key: /api/v1/auth/plex is the public login route. It creates
        the user only when they can already reach the media server and
        newPlexLogin is enabled, so this cannot grant access Overseerr would have
        refused. The session cookie it returns is discarded.

        Args:
            auth_token: The invited user's Plex auth token
            connection: Connection object with URL and API key

        Returns:
            Dict with 'status' and 'message' keys
        """
        if not connection.url:
            return {
                "status": "skipped",
                "message": "No Overseerr URL configured",
            }

        base_url = connection.url.rstrip("/")
        url = f"{base_url}/api/v1/auth/plex"
        total = len(_PROVISION_BACKOFF_SECONDS) + 1
        last_message = "Unknown error"

        session, headers, _ = _open_session(base_url)

        for attempt in range(1, total + 1):
            try:
                resp = session.post(
                    url,
                    json={"authToken": auth_token},
                    headers=headers,
                    timeout=10,
                )
            except Exception as exc:
                last_message = str(exc)
                logging.warning(
                    "Overseerr provisioning attempt %s/%s failed: %s",
                    attempt,
                    total,
                    exc,
                )
            else:
                if resp.ok:
                    logging.info(
                        "Overseerr provisioned Plex user via %s on attempt %s",
                        url,
                        attempt,
                    )
                    return {
                        "status": "success",
                        "message": "User created in Overseerr",
                    }

                # Carry the body, not just the status: a bare "HTTP 403" reads
                # like a rejected user when it can just as easily be a rejected
                # request, and the two need completely different fixes.
                body = (resp.text or "").strip()[:200]
                last_message = f"HTTP {resp.status_code} {body}".strip()

                if resp.status_code == 403 and "csrf" in body.lower():
                    # Overseerr's CSRF cookies are Secure, so they are never sent
                    # back over plain HTTP and the token can never validate. No
                    # amount of retrying fixes a configuration problem.
                    logging.warning(
                        "Overseerr rejected the request as CSRF-invalid. Its CSRF "
                        "cookies are Secure, so an http:// connection URL can "
                        "never satisfy them - configure %s over https, or turn "
                        "off CSRF protection in Overseerr.",
                        base_url,
                    )
                    break

                # A plain 403 is Overseerr saying the user cannot reach the media
                # server, which right after an invite may just mean plex.tv has
                # not published the share yet. Anything else will not fix itself.
                if resp.status_code != 403:
                    break
                logging.info(
                    "Overseerr does not see the share yet (attempt %s/%s)",
                    attempt,
                    total,
                )

            if attempt <= len(_PROVISION_BACKOFF_SECONDS):
                time.sleep(_PROVISION_BACKOFF_SECONDS[attempt - 1])

        logging.warning("Overseerr provisioning gave up: %s", last_message)
        return {"status": "error", "message": last_message}
