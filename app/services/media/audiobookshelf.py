from __future__ import annotations

import logging
import re
from typing import Any

from app.extensions import db
from app.models import Library, User

from .client_base import RestApiMixin, register_media_client

"""Audiobookshelf media server client.

This client provides functionality for Wizarr to:
  * validate connection credentials (URL & API token)
  * get server status and version information
  * scan and manage libraries
  * list, create, update, and delete users
  * track active sessions and server statistics
  * handle user invitations and library access

The implementation follows the official Audiobookshelf API patterns
and includes proper error handling, response validation, and support
for different response formats across ABS versions.
"""


@register_media_client("audiobookshelf")
class AudiobookshelfClient(RestApiMixin):
    """Very small wrapper around the Audiobookshelf REST API."""

    #: API prefix that all modern ABS endpoints share
    API_PREFIX = "/api"

    EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,7}$")

    def __init__(self, *args, **kwargs):
        # Provide defaults so legacy code keeps working if the caller didn't
        # specify explicit keys / MediaServer.
        if "url_key" not in kwargs:
            kwargs["url_key"] = "server_url"
        if "token_key" not in kwargs:
            kwargs["token_key"] = "api_key"

        super().__init__(*args, **kwargs)

        # Strip trailing slash to keep URL join sane.
        if self.url and self.url.endswith("/"):
            self.url = self.url.rstrip("/")

    # ------------------------------------------------------------------
    # Public API expected by Wizarr
    # ------------------------------------------------------------------

    def validate_connection(self) -> tuple[bool, str]:
        """Validate connection to Audiobookshelf server.
        
        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            # Try to get server status first (public endpoint)
            response = self.get("/status")
            response.raise_for_status()
            status_data = response.json()
            
            
            if not status_data.get("isInit", False):
                return False, "Server is not initialized"
            
            # If we have a token, validate it by trying to authorize
            if getattr(self, "token", None):
                auth_response = self.post(f"{self.API_PREFIX}/authorize")
                if auth_response.status_code == 401:
                    return False, "Invalid API token"
                auth_response.raise_for_status()
                
            return True, "Connection successful"
            
        except Exception as exc:
            logging.error("ABS: connection validation failed – %s", exc)
            return False, f"Connection failed: {str(exc)}"

    def get_server_status(self) -> dict[str, Any]:
        """Get server status information.
        
        Returns:
            dict: Server status data
        """
        try:
            response = self.get("/status")
            response.raise_for_status()
            return response.json()
        except Exception as exc:
            logging.error("ABS: failed to get server status – %s", exc)
            return {}

    # --- libraries -----------------------------------------------------

    def libraries(self) -> dict[str, str]:
        """Return mapping of ``library_id`` → ``display_name``.

        Audiobookshelf exposes ``GET /api/libraries`` which returns
        ``{"libraries": [ … ]}``.
        """
        try:
            response = self.get(f"{self.API_PREFIX}/libraries")
            response.raise_for_status()
            data = response.json()
            
            # Handle both direct array and wrapped response formats
            if isinstance(data, list):
                libs = data
            else:
                libs = data.get("libraries", [])
            
            return {item["id"]: item["name"] for item in libs if isinstance(item, dict)}
        except Exception as exc:
            logging.warning("ABS: failed to fetch libraries – %s", exc)
            return {}

    def scan_libraries(
        self, url: str | None = None, token: str | None = None
    ) -> dict[str, str]:
        """Scan available libraries on this Audiobookshelf server.

        Args:
            url: Optional server URL override
            token: Optional API token override

        Returns:
            dict: Library name -> library ID mapping
        """
        import requests

        if url and token:
            # Use override credentials for scanning
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            response = requests.get(
                f"{url.rstrip('/')}/api/libraries", 
                headers=headers, 
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            # Handle both direct array and wrapped response formats
            if isinstance(data, list):
                libs = data
            else:
                libs = data.get("libraries", [])
        else:
            # Use saved credentials
            response = self.get(f"{self.API_PREFIX}/libraries")
            response.raise_for_status()
            data = response.json()
            
            if isinstance(data, list):
                libs = data
            else:
                libs = data.get("libraries", [])

        return {item["name"]: item["id"] for item in libs if isinstance(item, dict)}

    def get_library(self, library_id: str) -> dict[str, Any]:
        """Get detailed information about a specific library.
        
        Args:
            library_id: The library ID to fetch
            
        Returns:
            dict: Library details
        """
        try:
            response = self.get(f"{self.API_PREFIX}/libraries/{library_id}")
            response.raise_for_status()
            return response.json()
        except Exception as exc:
            logging.error("ABS: failed to get library %s – %s", library_id, exc)
            return {}

    # --- users ---------------------------------------------------------

    def list_users(self) -> list[User]:
        """Read users from Audiobookshelf and reflect them locally."""
        server_id = getattr(self, "server_id", None)
        if server_id is None:
            return []

        try:
            response = self.get(f"{self.API_PREFIX}/users")
            response.raise_for_status()
            data = response.json()
            
            # Handle both direct array and wrapped response formats
            if isinstance(data, list):
                raw_users = data
            else:
                raw_users = data.get("users", [])
        except Exception as exc:
            logging.warning("ABS: failed to list users – %s", exc)
            return []

        raw_by_id = {u["id"]: u for u in raw_users}

        try:
            # Add new users or update existing ones
            for uid, remote in raw_by_id.items():
                db_row = User.query.filter_by(token=uid, server_id=server_id).first()
                if not db_row:
                    db_row = User(
                        token=uid,
                        username=remote.get("username", "abs-user"),
                        email=remote.get("email", ""),
                        code="empty",
                        server_id=server_id,
                    )
                    db.session.add(db_row)
                else:
                    db_row.username = remote.get("username", db_row.username)
                    db_row.email = remote.get("email", db_row.email)

            # Remove users that no longer exist upstream
            to_check = User.query.filter(User.server_id == server_id).all()
            for local in to_check:
                if local.token not in raw_by_id:
                    db.session.delete(local)

            db.session.commit()

        except Exception as exc:
            logging.error("ABS: failed to sync users – %s", exc)
            db.session.rollback()
            return []

        return User.query.filter(User.server_id == server_id).all()

    # --- user management ------------------------------------------------

    def create_user(
        self,
        username: str,
        password: str,
        email: str,
        *,
        is_admin: bool = False,
        allow_downloads: bool = True,
    ) -> str:
        """Create a user and return the Audiobookshelf user‐ID.

        The ABS API expects at least ``username``.  A password can be an
        empty string (guest), but Wizarr always passes one.
        """
        permissions = {
            "download": allow_downloads,
            "update": False,
            "delete": False,
            "upload": False,
            "accessAllLibraries": False,
            "accessAllTags": True,
            "accessExplicitContent": True,
        }

        payload = {
            "username": username,
            "password": password,
            "isActive": True,
            "email": email,
            "type": "admin" if is_admin else ("user" if allow_downloads else "guest"),
            "permissions": permissions,
        }
        try:
            resp = self.post(f"{self.API_PREFIX}/users", json=payload)
            self._handle_response_error(resp, "user creation")
            data = resp.json()
            
            # Handle different response formats
            user_id = data.get("id")
            if not user_id and "user" in data:
                user_id = data["user"].get("id")
            
            if not user_id:
                raise Exception("No user ID returned from server")
                
            return user_id
        except Exception as exc:
            logging.error("ABS: failed to create user – %s", exc)
            raise

    def update_user(self, user_id: str, payload: dict[str, Any]):
        """PATCH arbitrary fields on a user object."""
        try:
            resp = self.patch(f"{self.API_PREFIX}/users/{user_id}", json=payload)
            self._handle_response_error(resp, f"updating user {user_id}")
            return resp.json()
        except Exception as exc:
            logging.error("ABS: failed to update user %s – %s", user_id, exc)
            raise

    def delete_user(self, user_id: str):
        """Delete a user permanently from Audiobookshelf."""
        try:
            resp = self.delete(f"{self.API_PREFIX}/users/{user_id}")
            # 204 No Content or 200 are both acceptable
            if resp.status_code not in (200, 204):
                self._handle_response_error(resp, f"deleting user {user_id}")
        except Exception as exc:
            logging.error("ABS: failed to delete user %s – %s", user_id, exc)
            raise

    def get_user(self, user_id: str):
        """Return a full user object from Audiobookshelf."""
        response = self.get(f"{self.API_PREFIX}/users/{user_id}")
        response.raise_for_status()
        return response.json()

    # ------------------------------------------------------------------
    # Public sign-up (invite links)
    # ------------------------------------------------------------------

    def _password_for_db(self, password: str) -> str:
        """Return the password value to store in the local DB (plain)."""
        return password

    @staticmethod
    def _mark_invite_used(inv, user):
        inv.used_by = user
        from app.services.invites import mark_server_used

        mark_server_used(inv, user.server_id)

    def _set_specific_libraries(
        self, user_id: str, library_ids: list[str], allow_downloads: bool = True
    ):
        """Restrict the given *user* to the supplied library IDs.

        If *library_ids* is empty, the account will be granted access to all
        libraries (ABS default behaviour).
        """
        # Fetch current user object so that we do not accidentally wipe other fields
        try:
            current = self.get_user(user_id)
        except Exception as exc:
            logging.warning("ABS: failed to read user %s – %s", user_id, exc)
            return

        perms = current.get("permissions", {}) or {}
        perms["accessAllLibraries"] = not library_ids
        perms["download"] = allow_downloads

        patch = {
            "permissions": perms,
            # Root-level list of library IDs that the user may access
            "librariesAccessible": library_ids if library_ids else [],
            # Update user type based on download permission
            "type": "user" if allow_downloads else "guest",
        }

        try:
            self.update_user(user_id, patch)
        except Exception:
            logging.exception("ABS: failed to update permissions for %s", user_id)

    def join(self, username: str, password: str, confirm: str, email: str, code: str):
        """Public invite flow for Audiobookshelf users."""
        from sqlalchemy import or_

        from app.models import Invitation, User
        from app.services.invites import is_invite_valid

        if not self.EMAIL_RE.fullmatch(email):
            return False, "Invalid e-mail address."
        if not 8 <= len(password) <= 20:
            return False, "Password must be 8–20 characters."
        if password != confirm:
            return False, "Passwords do not match."

        ok, msg = is_invite_valid(code)
        if not ok:
            return False, msg

        server_id = getattr(self, "server_id", None)
        if server_id is None:
            return False, "Server configuration error"

        existing = User.query.filter(
            or_(User.username == username, User.email == email),
            User.server_id == server_id,
        ).first()
        if existing:
            return False, "User or e-mail already exists."

        try:
            inv = Invitation.query.filter_by(code=code).first()

            # Get download permission from invitation (default to True if not set)
            allow_downloads = getattr(inv, "allow_downloads", True)
            if allow_downloads is None:
                allow_downloads = True

            user_id = self.create_user(
                username, password, email=email, allow_downloads=allow_downloads
            )
            if not user_id:
                return False, "Failed to create user on server"

            # Set library access
            if inv and inv.libraries:
                lib_ids = [
                    lib.external_id
                    for lib in inv.libraries
                    if lib.server_id == server_id
                ]
            else:
                lib_ids = [
                    lib.external_id
                    for lib in Library.query.filter_by(
                        enabled=True, server_id=server_id
                    ).all()
                ]
            self._set_specific_libraries(user_id, lib_ids, allow_downloads)

            # Calculate expiry
            expires = None
            if inv and inv.duration:
                try:
                    import datetime as _dt

                    expires = _dt.datetime.utcnow() + _dt.timedelta(
                        days=int(inv.duration)
                    )
                except Exception:
                    pass

            # Store locally
            local = User(
                token=user_id,
                username=username,
                email=email,
                code=code,
                expires=expires,
                server_id=server_id,
            )
            db.session.add(local)
            db.session.commit()

            self._mark_invite_used(inv, local)
            return True, ""

        except Exception as exc:
            logging.error("ABS join failed: %s", exc)
            db.session.rollback()
            return False, "Failed to create user"

    def now_playing(self) -> list[dict]:
        """Return active sessions (updated within the last minute).

        AudioBookShelf lists sessions in chronological order (oldest first).
        We first fetch pagination metadata, then request the last page with
        10 items per page to retrieve the most recent sessions and filter
        them by activity timestamp.
        """
        import time

        endpoint = f"{self.API_PREFIX}/sessions"

        try:
            # --- Step 1: read pagination metadata with a minimal request ---------
            query_params = {"itemsPerPage": "1", "page": "0"}
            response = self.get(endpoint, params=query_params)
            response.raise_for_status()
            meta = response.json()

            total_sessions: int = meta.get("total", 0)
            if not total_sessions:
                return []  # Nothing playing at all

            # --- Step 2: fetch the last page with a fixed page size -------------
            items_per_page = 10  # sane default – plenty for a dashboard
            last_page = max(0, (total_sessions - 1) // items_per_page)  # zero-based
            
            query_params = {"itemsPerPage": str(items_per_page), "page": str(last_page)}
            sessions_response = self.get(endpoint, params=query_params)
            sessions_response.raise_for_status()
            sessions_data = sessions_response.json()
            sessions = sessions_data.get("sessions", [])
        except Exception as exc:
            logging.error("ABS: failed to fetch sessions – %s", exc)
            return []

        # ------------------------------------------------------------------
        # Build user-id → username mapping so dashboard shows names instead of
        # raw UUIDs.  One request is sufficient and relatively cheap.
        # ------------------------------------------------------------------
        user_name_by_id: dict[str, str] = {}
        try:
            users_response = self.get(f"{self.API_PREFIX}/users")
            users_response.raise_for_status()
            users_json = users_response.json()
            
            # Handle both direct array and wrapped response formats
            if isinstance(users_json, list):
                users_list = users_json
            else:
                users_list = users_json.get("users", [])
                
            for u in users_list:
                if isinstance(u, dict) and u.get("id"):
                    user_name_by_id[str(u["id"])] = u.get("username", "user")
        except Exception as exc:
            # If the call fails we fall back to raw IDs – no fatal error.
            logging.debug("ABS: failed to fetch user names for sessions – %s", exc)

        now_ms = int(time.time() * 1000)  # current time in ms (ABS uses ms)
        active: list[dict] = []

        for raw in sessions:
            if not isinstance(raw, dict):
                continue

            updated_at = raw.get("updatedAt")  # ms precision
            if updated_at is None or now_ms - updated_at > 60_000:  # > 1 min
                continue  # stale / finished session

            # --- basic metadata ------------------------------------------------
            session_id = str(raw.get("id", ""))
            user_id = str(raw.get("userId", ""))
            user_display = user_name_by_id.get(user_id, user_id)
            media_type = raw.get("mediaType", "book")
            title = raw.get("displayTitle", "Unknown")

            # --- progress ------------------------------------------------------
            pos = raw.get("currentTime", 0)  # seconds
            duration = raw.get("duration", 0) or 1  # avoid div-by-zero
            progress = max(0.0, min(1.0, pos / duration))

            # --- device / client ----------------------------------------------
            device_info = raw.get("deviceInfo", {})
            device_name = (
                f"{device_info.get('osName', '')} {device_info.get('browserName', '')}".strip()
                or "Unknown Device"
            )
            client = raw.get("mediaPlayer", "")

            # --- artwork -------------------------------------------------------

            # Primary & secondary artwork --------------------------------------
            poster_url: str | None = None
            thumb_url: str | None = None

            li_id = raw.get("libraryItemId")
            if li_id:
                # Cover endpoint (vertical poster)
                poster_url = f"{self.url}{self.API_PREFIX}/items/{li_id}/cover"

                # Try to leverage the preview/thumbnail endpoint if the server
                # version supports it.  ABS provides automatic resizing via the
                # optional width/height query params.  We keep it simple and
                # request a 400-pixel wide version which most dashboards can
                # display without additional processing.
                thumb_url = f"{poster_url}?width=400"

            # RSS image fallback – some podcast sessions won’t have a library
            # item ID.  In that case we rely on the RSS <image> URL which is
            # already a square thumbnail.
            if poster_url is None:
                meta = raw.get("mediaMetadata", {})
                poster_url = meta.get("imageUrl")
                thumb_url = poster_url

            artwork_url = poster_url

            # --- audio metadata ------------------------------------------------
            audio_metadata = self._get_audio_metadata(li_id, pos) if li_id else {}

            # --- transcoding ----------------------------------------------------
            play_method = raw.get("playMethod", 0)  # 0 = direct play
            transcoding_info = {
                "is_transcoding": False,
                "direct_play": play_method == 0,
            }
            
            session_data = {
                "user_name": user_display,
                "media_title": title,
                "media_type": media_type,
                "progress": progress,
                "state": "playing",  # ABS has no explicit pause flag yet
                "session_id": session_id,
                "client": client,
                "device_name": device_name,
                "position_ms": int(pos * 1000),
                "duration_ms": int(duration * 1000),
                "artwork_url": artwork_url,
                "thumbnail_url": thumb_url,
                "transcoding": transcoding_info,
            }
            
            # Add audio metadata if available
            if audio_metadata:
                session_data.update(audio_metadata)
                
            active.append(session_data)

        return active

    def _get_audio_metadata(self, library_item_id: str, current_position: float = 0) -> dict:
        """Fetch audio metadata for a library item, identifying the specific file being played.
        
        Args:
            library_item_id: The library item ID to fetch metadata for
            current_position: Current playback position in seconds to identify specific file
            
        Returns:
            dict: Audio metadata including bitrate, codec, format, etc.
        """
        try:
            # Fetch library item details
            response = self.get(f"{self.API_PREFIX}/items/{library_item_id}")
            response.raise_for_status()
            item_data = response.json()
            
            # Extract audio files metadata
            media = item_data.get("media", {})
            audio_files = media.get("audioFiles", [])
            
            if not audio_files:
                return {}
            
            # Determine which specific audio file is currently being played
            # based on the current position for multi-file audiobooks
            current_audio_file = self._find_current_audio_file(audio_files, current_position)
            primary_audio = current_audio_file or audio_files[0]  # fallback to first file
            
            # Get file metadata (nested under 'metadata' key)
            file_metadata = primary_audio.get("metadata", {})
            
            current_file_info = {
                "filename": file_metadata.get("filename", "Unknown"),
                "index": primary_audio.get("index", 0) if current_audio_file else 0
            }
            
            audio_metadata = {}
            
            # Extract bitrate (directly from audio file object)
            if "bitRate" in primary_audio:
                audio_metadata["bitrate"] = primary_audio["bitRate"]
                audio_metadata["bitrate_kbps"] = f"{primary_audio['bitRate'] // 1000} kbps" if primary_audio["bitRate"] else "Unknown"
            
            # Extract codec (directly from audio file object)
            if "codec" in primary_audio:
                audio_metadata["audio_codec"] = primary_audio["codec"]
            
            # Extract format (directly from audio file object)
            if "format" in primary_audio:
                audio_metadata["audio_format"] = primary_audio["format"]
            
            # Extract additional useful metadata
            if "duration" in primary_audio:
                audio_metadata["file_duration"] = primary_audio["duration"]
            
            if "size" in file_metadata:
                audio_metadata["file_size"] = file_metadata["size"]
                # Convert to human readable format
                size_mb = file_metadata["size"] / (1024 * 1024)
                audio_metadata["file_size_mb"] = f"{size_mb:.1f} MB"
            
            # Add essential file information
            audio_metadata["audio_file_count"] = len(audio_files)
            audio_metadata["current_file"] = current_file_info["filename"]
            audio_metadata["current_file_index"] = current_file_info["index"]
            
            return audio_metadata
            
        except Exception as exc:
            logging.warning("ABS: failed to fetch audio metadata for item %s – %s", library_item_id, exc)
            return {}
    
    def _find_current_audio_file(self, audio_files: list, current_position: float) -> dict | None:
        """Find which audio file is currently being played based on position.
        
        Args:
            audio_files: List of audio files from the library item
            current_position: Current playback position in seconds
            
        Returns:
            dict: The audio file currently being played, or None if not found
        """
        if not audio_files or current_position <= 0:
            return None
            
        # Calculate cumulative durations to find which file contains the current position
        cumulative_duration = 0
        
        for audio_file in audio_files:
            # Duration is directly on the audio file object, not in metadata
            file_duration = audio_file.get("duration", 0)
            
            # Check if current position falls within this file's duration
            if current_position <= cumulative_duration + file_duration:
                return audio_file
                
            cumulative_duration += file_duration
            
        # If position is beyond all files, return the last file
        return audio_files[-1] if audio_files else None



    def get_library_item_metadata(self, library_item_id: str) -> dict:
        """Get detailed metadata for a specific library item.
        
        Args:
            library_item_id: The library item ID to fetch metadata for
            
        Returns:
            dict: Complete library item data with enhanced audio metadata
        """
        try:
            # Fetch library item details
            response = self.get(f"{self.API_PREFIX}/items/{library_item_id}")
            response.raise_for_status()
            item_data = response.json()
            
            # Get enhanced audio metadata
            audio_metadata = self._get_audio_metadata(library_item_id, 0)
            
            # Add audio metadata to the response
            if audio_metadata:
                if "metadata" not in item_data:
                    item_data["metadata"] = {}
                item_data["metadata"]["audio_metadata"] = audio_metadata
                
                # Also add it at the top level for easier access
                item_data["audio_metadata"] = audio_metadata
            
            return item_data
            
        except Exception as exc:
            logging.error("ABS: failed to fetch library item metadata for %s – %s", library_item_id, exc)
            raise

    def statistics(self):
        """Return essential AudiobookShelf server statistics for the dashboard.

        Only collects data actually used by the UI:
        - Server version for health card (Unknown for ABS)
        - Active sessions count for health card
        - Transcoding sessions count for health card (always 0 for ABS)
        - Total users count for health card

        Returns:
            dict: Server statistics with minimal API calls
        """
        try:
            stats = {
                "library_stats": {},
                "user_stats": {},
                "server_stats": {},
                "content_stats": {},
            }

            # ------------------------------------------------------------------
            # Active sessions – reuse the same pagination / freshness logic as
            # *now_playing()* so numbers stay in sync across the dashboard.
            # ------------------------------------------------------------------
            try:
                active_sessions = self.now_playing()
            except Exception as exc:
                logging.error(
                    "ABS statistics: failed to calculate active sessions – %s", exc
                )
                active_sessions = []

            # ------------------------------------------------------------------
            # User statistics – we only need total count for the health card.
            # ------------------------------------------------------------------
            total_users = 0
            try:
                users_response = self.get(f"{self.API_PREFIX}/users")
                users_response.raise_for_status()
                users_data = users_response.json()
                
                # Handle both direct array and wrapped response formats
                if isinstance(users_data, list):
                    users_list = users_data
                else:
                    users_list = users_data.get("users", [])
                    
                total_users = len(users_list) if isinstance(users_list, list) else 0
            except Exception as exc:
                logging.error("ABS statistics: failed to fetch users – %s", exc)

            stats["user_stats"] = {
                "total_users": total_users,
                "active_sessions": len(active_sessions),
            }

            # ------------------------------------------------------------------
            # Server statistics – ABS doesn't expose version or transcoding
            # count via the API (yet) so we fill with sane defaults.
            # ------------------------------------------------------------------
            stats["server_stats"] = {
                "version": "Unknown",
                "transcoding_sessions": 0,
            }

            return stats

        except Exception as e:
            logging.error(f"Failed to get AudiobookShelf statistics: {e}")
            return {
                "library_stats": {},
                "user_stats": {},
                "server_stats": {},
                "content_stats": {},
                "error": str(e),
            }

    # RestApiMixin overrides -------------------------------------------------

    def _headers(self) -> dict[str, str]:  # type: ignore[override]
        """Return default headers including Authorization if a token is set."""
        headers: dict[str, str] = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        if getattr(self, "token", None):
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def _handle_response_error(self, response, context: str = ""):
        """Handle common response errors with better error messages."""
        if response.status_code == 401:
            raise Exception(f"Unauthorized: Invalid API token{' for ' + context if context else ''}")
        elif response.status_code == 403:
            raise Exception(f"Forbidden: Insufficient permissions{' for ' + context if context else ''}")
        elif response.status_code == 404:
            raise Exception(f"Not found{': ' + context if context else ''}")
        elif response.status_code >= 500:
            raise Exception(f"Server error ({response.status_code}){' for ' + context if context else ''}")
        else:
            response.raise_for_status()
