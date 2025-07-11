import datetime
import logging
import re
import base64
from typing import Dict, List, Any
from sqlalchemy import or_

from app.extensions import db
from app.models import Invitation, User, Library
from app.services.notifications import notify
from app.services.invites import is_invite_valid, mark_server_used
from .client_base import RestApiMixin, register_media_client

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,7}$")


@register_media_client("komga")
class KomgaClient(RestApiMixin):
    """Wrapper around the Komga REST API using Basic Authentication."""

    def __init__(self, *args, **kwargs):
        # Komga uses username/password for Basic Auth, not API keys
        if "url_key" not in kwargs:
            kwargs["url_key"] = "server_url"
        if "token_key" not in kwargs:
            kwargs["token_key"] = "api_key"  # Keep using api_key but parse it as username:password
        super().__init__(*args, **kwargs)
        
        # For Basic Auth, we need both username and password
        # Parse the token field as "username:password" format
        self.username = None
        self.password = None
        
        if self.token:
            if ':' in self.token:
                # Split username:password format
                parts = self.token.split(':', 1)
                self.username = parts[0]
                self.password = parts[1]
            else:
                # Fallback: assume it's just a password and use default username
                self.username = "admin"
                self.password = self.token

    def _headers(self) -> Dict[str, str]:
        headers = {"Accept": "application/json"}
        if self.username and self.password:
            # Use Basic Authentication instead of Bearer token
            credentials = f"{self.username}:{self.password}"
            encoded_credentials = base64.b64encode(credentials.encode()).decode()
            headers["Authorization"] = f"Basic {encoded_credentials}"
        return headers

    def libraries(self) -> Dict[str, str]:
        """Return mapping of library_id -> library_name."""
        try:
            response = self.get("/api/v1/libraries")
            libraries = response.json()
            return {
                lib["id"]: lib["name"]
                for lib in libraries
            }
        except Exception as e:
            logging.error(f"Failed to get Komga libraries: {e}")
            return {}

    def create_user(self, username: str, password: str, email: str) -> str:
        """Create a new Komga user and return the user ID."""
        # Corrected payload format based on actual Komga API
        payload = {
            "email": email,
            "password": password,
            "roles": ["USER"]
        }
        response = self.post("/api/v1/users", json=payload)
        return response.json()["id"]

    def update_user(self, user_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update a Komga user."""
        response = self.patch(f"/api/v1/users/{user_id}", json=updates)
        return response.json()

    def delete_user(self, user_id: str) -> None:
        """Delete a Komga user."""
        self.delete(f"/api/v1/users/{user_id}")

    def get_user(self, user_id: str) -> Dict[str, Any]:
        """Get a Komga user by ID."""
        response = self.get(f"/api/v1/users/{user_id}")
        return response.json()

    def list_users(self) -> List[User]:
        """Sync users from Komga into the local DB and return the list of User records."""
        try:
            response = self.get("/api/v1/users")
            komga_users = {u["id"]: u for u in response.json()}

            for komga_user in komga_users.values():
                existing = User.query.filter_by(token=komga_user["id"]).first()
                if not existing:
                    new_user = User(
                        token=komga_user["id"],
                        username=komga_user["email"],
                        email=komga_user["email"],
                        code="empty",
                        server_id=getattr(self, 'server_id', None),
                    )
                    db.session.add(new_user)
            db.session.commit()

            to_check = (
                User.query
                .filter(User.server_id == getattr(self, 'server_id', None))
                .all()
            )
            for db_user in to_check:
                if db_user.token not in komga_users:
                    db.session.delete(db_user)
            db.session.commit()

            return (
                User.query
                .filter(User.server_id == getattr(self, 'server_id', None))
                .all()
            )
        except Exception as e:
            logging.error(f"Failed to list Komga users: {e}")
            return []

    def _set_library_access(self, user_id: str, library_ids: List[str]) -> None:
        """Set library access for a user."""
        if not library_ids:
            return
        
        try:
            for library_id in library_ids:
                self.put(f"/api/v1/users/{user_id}/shared-libraries/{library_id}")
        except Exception as e:
            logging.warning(f"Failed to set library access for user {user_id}: {e}")

    def join(
        self, username: str, password: str, confirm: str, email: str, code: str
    ) -> tuple[bool, str]:
        """Handle public sign-up via invite for Komga servers."""
        if not EMAIL_RE.fullmatch(email):
            return False, "Invalid e-mail address."
        if not 8 <= len(password) <= 20:
            return False, "Password must be 8–20 characters."
        if password != confirm:
            return False, "Passwords do not match."

        ok, msg = is_invite_valid(code)
        if not ok:
            return False, msg

        existing = User.query.filter(
            or_(User.username == username, User.email == email),
            User.server_id == getattr(self, 'server_id', None)
        ).first()
        if existing:
            return False, "User or e-mail already exists."

        try:
            user_id = self.create_user(username, password, email)

            inv = Invitation.query.filter_by(code=code).first()

            if inv.libraries:
                library_ids = [lib.external_id for lib in inv.libraries if lib.server_id == (inv.server.id if inv.server else None)]
            else:
                library_ids = [
                    lib.external_id
                    for lib in Library.query.filter_by(enabled=True, server_id=inv.server.id if inv.server else None).all()
                ]

            self._set_library_access(user_id, library_ids)

            expires = None
            if inv.duration:
                days = int(inv.duration)
                expires = datetime.datetime.utcnow() + datetime.timedelta(days=days)

            new_user = User(
                username=username,
                email=email,
                token=user_id,
                code=code,
                expires=expires,
                server_id=inv.server.id if inv.server else None,
            )
            db.session.add(new_user)
            db.session.commit()

            inv.used_by = new_user
            mark_server_used(inv, getattr(new_user, "server_id", None) or (inv.server.id if inv.server else None))

            notify(
                "New User",
                f"User {username} has joined your server! 🎉",
                tags="tada",
            )

            return True, ""

        except Exception:
            logging.error("Komga join error", exc_info=True)
            db.session.rollback()
            return False, "An unexpected error occurred."

    def now_playing(self) -> List[Dict[str, Any]]:
        """Return a list of currently playing sessions from Komga.
        
        Note: Komga is a comic/manga server and doesn't provide session 
        tracking or "now playing" functionality like media streaming servers.
        This method always returns an empty list.
        
        Returns:
            list: Always returns an empty list since Komga doesn't track active sessions.
        """
        logging.debug("Komga: No session tracking available - Komga doesn't provide now-playing functionality")
        return []

    def statistics(self) -> Dict[str, Any]:
        """Return comprehensive Komga server statistics.
        
        Returns:
            dict: Server statistics including library counts, user activity, etc.
        """
        try:
            stats = {
                "library_stats": {},
                "user_stats": {},
                "server_stats": {},
                "content_stats": {}
            }
            
            # Library statistics
            try:
                libraries_response = self.get("/api/v1/libraries").json()
                library_stats = {}
                
                for lib in libraries_response:
                    lib_type = "comics"
                    if lib_type not in library_stats:
                        library_stats[lib_type] = {
                            "count": 0,
                            "sections": []
                        }
                    
                    try:
                        series_response = self.get(f"/api/v1/libraries/{lib['id']}/series", params={"size": 1}).json()
                        series_count = series_response.get("totalElements", 0)
                        
                        library_stats[lib_type]["count"] += series_count
                        library_stats[lib_type]["sections"].append({
                            "name": lib["name"],
                            "size": series_count,
                            "id": lib["id"]
                        })
                    except Exception as e:
                        logging.warning(f"Failed to get series count for library {lib['name']}: {e}")
                        library_stats[lib_type]["sections"].append({
                            "name": lib["name"],
                            "size": 0,
                            "id": lib["id"]
                        })
                
                stats["library_stats"] = library_stats
            except Exception as e:
                logging.error(f"Failed to get Komga library stats: {e}")
                stats["library_stats"] = {}
            
            # User statistics
            try:
                users_response = self.get("/api/v1/users").json()
                total_users = len(users_response)
                
                stats["user_stats"] = {
                    "total_users": total_users,
                    "active_users": 0,
                    "active_sessions": 0
                }
            except Exception as e:
                logging.error(f"Failed to get Komga user stats: {e}")
                stats["user_stats"] = {
                    "total_users": 0,
                    "active_users": 0,
                    "active_sessions": 0
                }
            
            # Server statistics  
            try:
                actuator_response = self.get("/api/v1/actuator/info").json()
                
                total_series = 0
                total_books = 0
                try:
                    libraries_response = self.get("/api/v1/libraries").json()
                    for lib in libraries_response:
                        try:
                            series_response = self.get(f"/api/v1/libraries/{lib['id']}/series", params={"size": 1}).json()
                            total_series += series_response.get("totalElements", 0)
                            
                            books_response = self.get(f"/api/v1/libraries/{lib['id']}/books", params={"size": 1}).json()
                            total_books += books_response.get("totalElements", 0)
                        except Exception:
                            pass
                except Exception:
                    pass
                
                stats["server_stats"] = {
                    "version": actuator_response.get("build", {}).get("version", "Unknown"),
                    "server_name": "Komga Server",
                    "total_series": total_series,
                    "total_books": total_books,
                    "total_sessions": 0,
                    "transcoding_sessions": 0
                }
            except Exception as e:
                logging.error(f"Failed to get Komga server stats: {e}")
                stats["server_stats"] = {}
            
            # Content statistics
            try:
                content_stats = {
                    "recently_added": [],
                    "popular_series": [],
                    "reading_progress": []
                }
                
                # Get recently added series
                try:
                    recent_response = self.get("/api/v1/series", params={
                        "size": 5,
                        "sort": "createdDate,desc"
                    }).json()
                    
                    for series in recent_response.get("content", []):
                        content_stats["recently_added"].append({
                            "title": series.get("metadata", {}).get("title", "Unknown"),
                            "type": "series",
                            "added_at": series.get("createdDate"),
                            "library": series.get("libraryId", "Unknown")
                        })
                except Exception as e:
                    logging.warning(f"Failed to get recently added series: {e}")
                
                stats["content_stats"] = content_stats
            except Exception as e:
                logging.error(f"Failed to get Komga content stats: {e}")
                stats["content_stats"] = {}
            
            return stats
            
        except Exception as e:
            logging.error(f"Failed to get Komga statistics: {e}")
            return {
                "library_stats": {},
                "user_stats": {},
                "server_stats": {},
                "content_stats": {},
                "error": str(e)
            }