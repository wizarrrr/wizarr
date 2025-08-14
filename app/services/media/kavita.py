import datetime
import hashlib
import logging
import re
import time
from typing import TYPE_CHECKING
from urllib.parse import parse_qs, urlparse

from sqlalchemy import or_

from app.extensions import db
from app.models import Invitation, User
from app.services.invites import is_invite_valid

from .client_base import RestApiMixin, register_media_client

if TYPE_CHECKING:
    from app.services.media.user_details import MediaUserDetails

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,7}$")

# Global token cache: {cache_key: (jwt_token, expiry_time)}
_JWT_TOKEN_CACHE = {}


@register_media_client("kavita")
class KavitaClient(RestApiMixin):
    """Wrapper around the Kavita REST API for manga/comic management."""

    def __init__(self, *args, **kwargs):
        # Ensure default url/token keys if caller didn't override.
        if "url_key" not in kwargs:
            kwargs["url_key"] = "server_url"
        if "token_key" not in kwargs:
            kwargs["token_key"] = "api_key"

        super().__init__(*args, **kwargs)
        # Create a unique cache key for this server instance
        self._cache_key = self._generate_cache_key()

    def _generate_cache_key(self) -> str:
        """Generate a unique cache key based on server URL and API key."""
        if not self.url or not self.token:
            return ""

        # Create a hash of the URL and API key for the cache key
        cache_string = f"{self.url}:{self.token}"
        return hashlib.md5(cache_string.encode()).hexdigest()

    def _get_cached_token(self) -> str | None:
        """Get cached JWT token if it's still valid."""
        if not self._cache_key:
            return None

        cached_data = _JWT_TOKEN_CACHE.get(self._cache_key)
        if not cached_data:
            return None

        jwt_token, expiry_time = cached_data

        # Check if token has expired (with 30 second buffer)
        if time.time() >= expiry_time - 30:
            # Token expired, remove from cache
            _JWT_TOKEN_CACHE.pop(self._cache_key, None)
            return None

        return jwt_token

    def _cache_token(self, jwt_token: str, expires_in: int = 3600) -> None:
        """Cache the JWT token with expiry time."""
        if not self._cache_key or not jwt_token:
            return

        expiry_time = time.time() + expires_in
        _JWT_TOKEN_CACHE[self._cache_key] = (jwt_token, expiry_time)
        logging.info(f"Cached Kavita JWT token for {expires_in} seconds")

    # RestApiMixin overrides -------------------------------------------

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}

        # Try to get cached token first
        jwt_token = self._get_cached_token()

        # If no valid cached token, authenticate to get a new one
        if not jwt_token:
            jwt_token = self._authenticate_with_api_key()

        if jwt_token:
            headers["Authorization"] = f"Bearer {jwt_token}"
        return headers

    def _authenticate_with_api_key(self) -> str:
        """Use API key to get JWT token from Kavita."""
        if not self.token:
            return ""

        try:
            import requests

            # Make direct request to avoid circular dependency with _headers()
            # Include pluginName parameter as shown in Kavita docs
            url = f"{(self.url or '').rstrip('/')}/api/Plugin/authenticate"
            params = {"apiKey": self.token, "pluginName": "Wizarr"}
            headers = {"Content-Type": "application/json"}

            logging.info(f"Authenticating with Kavita API (cache miss): {url}")
            response = requests.post(url, params=params, headers=headers, timeout=10)

            response.raise_for_status()

            data = response.json()

            # The response should contain the JWT token
            jwt_token = data.get("token", "")
            if jwt_token:
                logging.info("Successfully authenticated with Kavita API")
                # Cache the token for 1 hour (JWT tokens typically expire after some time)
                self._cache_token(jwt_token, expires_in=3600)
                return jwt_token
            logging.error("No JWT token returned from Kavita authentication")
            return ""

        except Exception as e:
            logging.error(f"Failed to authenticate with Kavita API: {e}")
            return ""

    def libraries(self) -> dict[str, str]:
        """Get all libraries from Kavita."""
        try:
            response = self.get("/api/Library/libraries")
            libraries = response.json()
            return {str(lib["id"]): lib["name"] for lib in libraries}
        except Exception as e:
            logging.error(f"Failed to get Kavita libraries: {e}")
            return {}

    def scan_libraries(
        self, url: str | None = None, token: str | None = None
    ) -> dict[str, str]:
        """Scan available libraries on this Kavita server.

        Args:
            url: Optional server URL override
            token: Optional API token override

        Returns:
            dict: Library name -> library ID mapping
        """
        import requests

        if url and token:
            # Use override credentials for scanning - need to authenticate first
            try:
                auth_url = f"{url.rstrip('/')}/api/Plugin/authenticate"
                params = {"apiKey": token, "pluginName": "Wizarr"}
                auth_response = requests.post(
                    auth_url,
                    params=params,
                    headers={"Content-Type": "application/json"},
                    timeout=10,
                )
                auth_response.raise_for_status()
                jwt_token = auth_response.json().get("token", "")

                # Use JWT to get libraries
                headers = {
                    "Authorization": f"Bearer {jwt_token}",
                    "Content-Type": "application/json",
                }
                response = requests.get(
                    f"{url.rstrip('/')}/api/Library/libraries",
                    headers=headers,
                    timeout=10,
                )
                response.raise_for_status()
                libraries = response.json()
            except Exception as e:
                logging.error(
                    f"Failed to authenticate with Kavita using override credentials: {e}"
                )
                return {}
        else:
            # Use saved credentials
            try:
                response = self.get("/api/Library/libraries")
                libraries = response.json()
            except Exception as e:
                logging.error(
                    f"Failed to get Kavita libraries with saved credentials: {e}"
                )
                return {}

        return {lib["name"]: str(lib["id"]) for lib in libraries}

    def create_user(
        self,
        username: str,
        password: str,
        email: str = "",
        library_ids: list[str] | None = None,
    ) -> str:
        """Create a new user in Kavita using invite + confirm-email flow.

        Note: Kavita uses an invite-based system. The /api/Account/register endpoint
        only works for the initial admin user. For subsequent users, we must use
        the /api/Account/invite endpoint followed by /api/Account/confirm-email.
        """
        user_email = email or f"{username}@wizarr.local"

        try:
            # Step 1: Send invitation
            logging.info(f"Sending invite to {user_email} on Kavita")

            # Convert library IDs to integers for Kavita API
            kavita_library_ids = []
            if library_ids:
                for lib_id in library_ids:
                    try:
                        kavita_library_ids.append(int(lib_id))
                    except (ValueError, TypeError):
                        logging.warning(f"Invalid library ID for Kavita: {lib_id}")

            invite_data = {
                "email": user_email,
                "roles": ["Login"],
                "libraries": kavita_library_ids,
                "ageRestriction": {"ageRating": 0, "includeUnknowns": True},
            }
            invite_response = self.post("/api/Account/invite", json=invite_data)

            try:
                invite_response.raise_for_status()
            except Exception as exc:
                logging.error(
                    f"Invite failed: {invite_response.status_code} - {invite_response.text}"
                )
                raise Exception(
                    f"Invite failed: {invite_response.status_code} - {invite_response.text}"
                ) from exc

            invite_info = invite_response.json()

            # Extract the token from the emailLink, handling possible extra arguments after the token
            email_link = invite_info.get("emailLink", "")
            if not email_link:
                raise Exception("No emailLink found in Kavita invite response")

            # Defensive: parse token from emailLink (may be in query or fragment)
            invite_token = None
            parsed = urlparse(email_link)
            # Try query first
            params = parse_qs(parsed.query)
            invite_token = params.get("token", [None])[0]
            # If not found, try fragment (some Kavita versions use #token=...)
            if not invite_token and parsed.fragment:
                frag_params = parse_qs(parsed.fragment)
                invite_token = frag_params.get("token", [None])[0]

            if not invite_token:
                logging.error(
                    f"Could not extract invitation token from emailLink: {email_link}"
                )
                raise Exception("No invitation token found in response")

            # Step 3: Confirm email with username and password
            logging.info(f"Confirming email for user {username}")
            confirm_data = {
                "token": invite_token,
                "password": password,
                "username": username,
                "email": user_email,
            }
            confirm_response = self.post(
                "/api/Account/confirm-email", json=confirm_data
            )

            if confirm_response.status_code != 200:
                raise Exception(
                    f"Email confirmation failed: {confirm_response.status_code} - {confirm_response.text}"
                )

            # Step 4: Get user ID
            users_response = self.get("/api/Users")

            if users_response.status_code != 200:
                logging.warning(f"Could not get users: {users_response.status_code}")
                return user_email  # Use email as fallback

            # Check if response has content before parsing JSON
            if not users_response.text.strip():
                logging.warning("Users API returned empty response")
                return user_email  # Use email as fallback

            try:
                users = users_response.json()

                for user in users:
                    uname = user.get("username") or user.get("userName")
                    if uname == username or user.get("email") == user_email:
                        return str(user["id"])
                        # Roles and library permissions are now correctly applied by the
                        # invitation workflow itself (Kavita ≥ 0.8.3). No extra patch-up
                        # calls are necessary.

                # User created successfully but not found in list yet - use email
                return user_email

            except Exception as json_exc:
                logging.warning(f"Could not parse users JSON: {json_exc}")
                return user_email  # Use email as fallback

        except Exception as exc:
            logging.error(f"Failed to create user in Kavita: {exc}")
            raise Exception(f"Failed to create user in Kavita: {exc}") from exc

    def delete_user(self, user_identifier: str) -> None:
        """Delete a user from Kavita.

        Kavita **only** accepts the *username* on `DELETE /api/Users/delete-user`.
        However, internally Wizarr often stores the remote *numeric id* in the
        `User.token` column.  To stay compatible we accept *either* value:

        1. If the caller passes a string containing non-digits, we treat it as
           the username directly.
        2. If it looks like a purely numeric id we first resolve it to the
           corresponding username via `GET /api/Users`.

        Once we have the username we forward the request to Kavita.
        """

        # Fast-path: already a username
        if not user_identifier.isdigit():
            username = user_identifier
        else:
            username = None
            try:
                users = self.get("/api/Users").json()
                if isinstance(users, list):
                    for u in users:
                        if str(u.get("id")) == user_identifier:
                            username = u.get("username") or u.get("userName")
                            break
                if not username:
                    logging.warning(
                        "Could not map Kavita user-id %s to username – aborting deletion",
                        user_identifier,
                    )
                    return  # Gracefully exit – nothing to delete
            except Exception as exc:
                logging.error(
                    "Failed to resolve Kavita user-id %s → username: %s",
                    user_identifier,
                    exc,
                )
                return

        # Issue the deletion request
        try:
            self.delete(f"/api/Users/delete-user?username={username}")
            logging.info("Deleted Kavita user '%s'", username)
        except Exception as exc:
            logging.error(
                "Remote deletion failed for Kavita user '%s': %s", username, exc
            )

    def get_user(self, username: str) -> dict | None:
        """Get user info in legacy format for backward compatibility."""
        try:
            details = self.get_user_details(username)
            return {
                "id": details.user_id,
                "username": details.username,
                "email": details.email,
                "isAdmin": details.is_admin,
                "created": details.created_at.isoformat() + "Z"
                if details.created_at
                else None,
                "lastActive": details.last_active.isoformat() + "Z"
                if details.last_active
                else None,
            }
        except ValueError:
            return None

    def get_user_details(self, username: str) -> "MediaUserDetails":
        """Get detailed user information in standardized format."""
        from app.services.media.user_details import MediaUserDetails

        # Get raw user data from Kavita API
        try:
            all_users = self.get("/api/Users").json()
        except Exception as exc:
            logging.error("Failed to list Kavita users: %s", exc)
            raise ValueError(f"Failed to fetch Kavita users: {exc}") from exc

        if not isinstance(all_users, list):
            logging.warning(
                "Unexpected response format from /api/Users – expected list"
            )
            raise ValueError("Unexpected response format from Kavita API")

        raw_user = None
        for u in all_users:
            if not isinstance(u, dict):
                continue
            if u.get("username") == username:
                raw_user = u
                break

        if not raw_user:
            raise ValueError(f"Kavita user not found: {username}")

        # Get all available libraries for this server since Kavita gives full access
        from app.models import Library
        from app.services.media.user_details import UserLibraryAccess

        libs_q = (
            Library.query.filter_by(server_id=self.server_id, enabled=True)
            .order_by(Library.name)
            .all()
        )
        library_access = [
            UserLibraryAccess(
                library_id=lib.external_id, library_name=lib.name, has_access=True
            )
            for lib in libs_q
        ]

        return MediaUserDetails(
            user_id=str(raw_user.get("id", username)),
            username=raw_user.get("username", username),
            email=raw_user.get("email"),
            is_admin=raw_user.get("isAdmin", False),
            is_enabled=True,  # Kavita doesn't seem to have disabled users concept
            created_at=datetime.datetime.fromisoformat(raw_user["created"].rstrip("Z"))
            if raw_user.get("created")
            else None,
            last_active=datetime.datetime.fromisoformat(
                raw_user["lastActive"].rstrip("Z")
            )
            if raw_user.get("lastActive")
            else None,
            library_access=library_access,
            raw_policies=raw_user,
        )

    def update_user(self, username: str, form: dict) -> dict | None:
        """Update user *username* in Kavita."""
        try:
            current = self.get_user(username)

            # Update fields that exist in form
            for key, val in form.items():
                if current and key in current:
                    current[key] = val

            response = self.post("/api/Account/update", json=current)
            return response.json()
        except Exception as e:
            logging.error(f"Failed to update Kavita user {username}: {e}")
            return None

    def grant_library_access(self, user_id: str, library_ids: list[str]) -> None:
        """Grant user access to specific libraries."""
        for library_id in library_ids:
            try:
                self.post(
                    "/api/Library/grant-access",
                    json={"userId": int(user_id), "libraryId": int(library_id)},
                )
            except Exception as e:
                logging.error(
                    f"Failed to grant library {library_id} access to user {user_id}: {e}"
                )

    def list_users(self) -> list[User]:
        """Sync users from Kavita into the local DB and return the list of User records."""
        try:
            # Fetch users from Kavita
            response = self.get("/api/Users")

            # Kavita sometimes returns a 200 with an empty body when the JWT is expired
            if not response.text or not response.text.strip():
                logging.warning(
                    "Kavita /api/User returned an empty response – skipping user sync"
                )
                return []

            try:
                kavita_users = response.json()
            except Exception as json_exc:
                logging.error(f"Failed to decode Kavita users JSON: {json_exc}")
                return []

            if not isinstance(kavita_users, list):
                logging.warning(
                    "Unexpected response format from Kavita /api/User – expected list"
                )
                return []

            users_dict = {str(u["id"]): u for u in kavita_users}

            for kavita_user in users_dict.values():
                existing = User.query.filter_by(token=str(kavita_user["id"])).first()
                if not existing:
                    new = User(
                        token=str(kavita_user["id"]),
                        username=kavita_user.get("username")
                        or kavita_user.get("userName", "kavita-user"),
                        email=kavita_user.get("email", "empty"),
                        code="empty",
                        server_id=getattr(self, "server_id", None),
                    )
                    db.session.add(new)
            db.session.commit()

            # delete local users for this server that no longer exist upstream
            to_check = User.query.filter(
                User.server_id == getattr(self, "server_id", None)
            ).all()
            for dbu in to_check:
                if dbu.token not in users_dict:
                    db.session.delete(dbu)
            db.session.commit()

            # Get users with default policy information
            users = User.query.filter(
                User.server_id == getattr(self, "server_id", None)
            ).all()

            # Add default policy attributes (Kavita doesn't have specific download/live TV policies)
            for user in users:
                user.allow_downloads = True  # Default to True for reading apps
                user.allow_live_tv = False  # Kavita doesn't have Live TV
                user.allow_sync = True  # Default to True for reading apps

            return users
        except Exception as e:
            logging.error(f"Failed to sync Kavita users: {e}")
            return []

    # --- helpers -----------------------------------------------------

    def _password_for_db(self, password: str) -> str:
        """Return the password value to store in the local DB."""
        return password

    # --- public sign-up ---------------------------------------------

    def _do_join(
        self, username: str, password: str, confirm: str, email: str, code: str
    ) -> tuple[bool, str]:
        if email and not EMAIL_RE.fullmatch(email):
            return False, "Invalid e-mail address."
        if not 8 <= len(password) <= 128:
            return False, "Password must be 8–128 characters."
        if password != confirm:
            return False, "Passwords do not match."

        ok, msg = is_invite_valid(code)
        if not ok:
            return False, msg

        existing = User.query.filter(
            or_(User.username == username, User.email == email),
            User.server_id == getattr(self, "server_id", None),
        ).first()
        if existing:
            return False, "User already exists."

        try:
            inv = Invitation.query.filter_by(code=code).first()
            current_server_id = getattr(self, "server_id", None)

            # Get library IDs for this server from the invitation
            library_ids = []
            if inv and inv.libraries:
                library_ids = [
                    str(lib.external_id)
                    for lib in inv.libraries
                    if lib.server_id == current_server_id
                ]

            # Create user in Kavita with library access
            user_identifier = self.create_user(username, password, email, library_ids)

            from app.services.expiry import calculate_user_expiry

            expires = calculate_user_expiry(inv, current_server_id) if inv else None

            # Store the user info in Wizarr's database
            # The token field contains either the user ID or email as fallback
            self._create_user_with_identity_linking(
                {
                    "username": username,
                    "email": email or "empty",
                    "token": user_identifier,  # User ID if successful, email as fallback
                    "code": code,
                    "expires": expires,
                    "server_id": current_server_id,
                }
            )
            db.session.commit()

            # Try to grant library access as fallback (in case invite didn't include libraries)
            if library_ids:
                try:
                    if user_identifier.isdigit():
                        # We have a numeric user ID, use it directly
                        self.grant_library_access(user_identifier, library_ids)
                        logging.info(
                            f"Granted library access to Kavita user {username} (ID: {user_identifier}): {library_ids}"
                        )
                    else:
                        # We have email identifier, try to find the actual user ID
                        logging.info(
                            f"Attempting to grant library access using email identifier: {user_identifier}"
                        )
                        try:
                            users_response = self.get("/api/Users")
                            if (
                                users_response.status_code == 200
                                and users_response.text.strip()
                            ):
                                users = users_response.json()
                                for user in users:
                                    uname2 = user.get("username") or user.get(
                                        "userName"
                                    )
                                    if uname2 == username or user.get("email") == email:
                                        found_user_id = str(user["id"])
                                        self.grant_library_access(
                                            found_user_id, library_ids
                                        )
                                        logging.info(
                                            f"Granted library access to Kavita user {username} (found ID: {found_user_id}): {library_ids}"
                                        )
                                        break
                                else:
                                    logging.warning(
                                        f"Could not find user {username} in user list for library access"
                                    )
                            else:
                                logging.warning(
                                    "Could not retrieve user list for library access granting"
                                )
                        except Exception as find_exc:
                            logging.warning(
                                f"Failed to find user ID for library access: {find_exc}"
                            )
                except Exception as e:
                    logging.warning(
                        f"Failed to grant library access for Kavita user {username}: {e}"
                    )
            else:
                logging.info(f"No libraries specified for Kavita user {username}")

            return (
                True,
                f"User '{username}' has been successfully created in Kavita and can now log in.",
            )

        except Exception:
            logging.error("Kavita join error", exc_info=True)
            db.session.rollback()
            return False, "An unexpected error occurred."

    def now_playing(self) -> list[dict]:
        return []

    def statistics(self):
        """Return Kavita server statistics for the dashboard.

        Returns:
            dict: Server statistics
        """
        try:
            stats = {
                "library_stats": {},
                "user_stats": {},
                "server_stats": {},
                "content_stats": {},
            }

            # Get server info - try different endpoints as /api/Server/server-info might not exist
            try:
                # Try the system info endpoint instead
                response = self.get("/api/System/info")
                if response.text.strip():  # Check if response has content
                    server_info = response.json()
                    stats["server_stats"] = {
                        "version": server_info.get("kavitaVersion", "Unknown"),
                        "transcoding_sessions": 0,  # Not applicable for Kavita
                    }
                else:
                    # Fallback: just set a default version
                    stats["server_stats"] = {
                        "version": "0.8.x",
                        "transcoding_sessions": 0,
                    }
            except Exception as e:
                logging.error(f"Failed to get Kavita server info: {e}")
                stats["server_stats"] = {
                    "version": "Unknown",
                    "transcoding_sessions": 0,
                }

            # Get user count
            try:
                response = self.get("/api/Users")
                if response.text.strip():  # Check if response has content
                    users = response.json()
                    user_count = len(users) if isinstance(users, list) else 0
                else:
                    user_count = 0

                stats["user_stats"] = {
                    "total_users": user_count,
                    "active_sessions": 0,  # Kavita doesn't track active sessions
                }
            except Exception as e:
                logging.error(f"Failed to get Kavita user stats: {e}")
                stats["user_stats"] = {"total_users": 0, "active_sessions": 0}

            # Get library stats
            try:
                response = self.get("/api/Library/libraries")
                if response.text.strip():  # Check if response has content
                    libraries = response.json()
                    if isinstance(libraries, list):
                        stats["library_stats"] = {"total_libraries": len(libraries)}

                        # Get series count - use a simpler approach
                        total_series = 0
                        try:
                            series_response = self.get(
                                "/api/Series", params={"pageSize": 1}
                            )
                            if series_response.text.strip():
                                series_data = series_response.json()
                                total_series = series_data.get("totalCount", 0)
                        except Exception:
                            total_series = 0

                        stats["content_stats"] = {"total_series": total_series}
                    else:
                        stats["library_stats"] = {"total_libraries": 0}
                        stats["content_stats"] = {"total_series": 0}
                else:
                    stats["library_stats"] = {"total_libraries": 0}
                    stats["content_stats"] = {"total_series": 0}

            except Exception as e:
                logging.error(f"Failed to get Kavita library stats: {e}")
                stats["library_stats"] = {"total_libraries": 0}
                stats["content_stats"] = {"total_series": 0}

            return stats

        except Exception as e:
            logging.error(f"Failed to get Kavita statistics: {e}")
            return {
                "library_stats": {},
                "user_stats": {},
                "server_stats": {},
                "content_stats": {},
                "error": str(e),
            }
