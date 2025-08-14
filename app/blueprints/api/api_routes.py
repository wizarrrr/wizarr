"""Flask-RESTX API routes with OpenAPI documentation."""

import datetime
import hashlib
import logging
import traceback
from functools import wraps

from flask import Blueprint, request
from flask_restx import Resource, abort

from app.extensions import api, db
from app.models import ApiKey, Invitation, Library, MediaServer, User
from app.services.invites import create_invite
from app.services.media.service import delete_user, list_users_all_servers
from app.services.server_name_resolver import get_display_name_info

from .models import (
    api_key_list_model,
    error_model,
    invitation_create_request,
    invitation_create_response,
    invitation_list_model,
    library_list_model,
    server_list_model,
    status_model,
    success_message_model,
    user_extend_request,
    user_extend_response,
    user_list_model,
)

# Create the Blueprint for the API
api_bp = Blueprint("api", __name__, url_prefix="/api")

# Initialize Flask-RESTX with the blueprint
api.init_app(api_bp)

# Set up logging
logger = logging.getLogger("wizarr.api")

# Create namespaces for organizing endpoints
status_ns = api.namespace("status", description="System status operations")
users_ns = api.namespace("users", description="User management operations")
invitations_ns = api.namespace(
    "invitations", description="Invitation management operations"
)
libraries_ns = api.namespace("libraries", description="Library information operations")
servers_ns = api.namespace("servers", description="Server information operations")
api_keys_ns = api.namespace("api-keys", description="API key management operations")


def require_api_key(f):
    """Decorator to require valid API key for endpoint access."""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_key = request.headers.get("X-API-Key")
        if not auth_key:
            logger.warning("API request without API key from %s", request.remote_addr)
            abort(401, error="Unauthorized")

        # Hash the provided key to compare with stored hash
        key_hash = hashlib.sha256(auth_key.encode()).hexdigest()
        api_key = ApiKey.query.filter_by(key_hash=key_hash, is_active=True).first()

        if not api_key:
            logger.warning(
                "API request with invalid API key from %s", request.remote_addr
            )
            abort(401, error="Unauthorized")

        # Update last used timestamp
        api_key.last_used_at = datetime.datetime.now(datetime.UTC)
        db.session.commit()

        logger.info(
            "API request authenticated with key '%s' from %s",
            api_key.name,
            request.remote_addr,
        )
        return f(*args, **kwargs)

    return decorated_function


def _generate_invitation_url(code):
    """Generate full invitation URL for the given code."""
    try:
        from flask import url_for

        # Try to generate URL using url_for with the public blueprint's invite route
        invite_path = url_for("public.invite", code=code, _external=False)

        # Get the host from the current request if available
        host = request.headers.get("Host")
        if host and not host.startswith("localhost"):
            # Only generate full URL for non-localhost hosts
            scheme = "https" if request.is_secure else "http"
            return f"{scheme}://{host}{invite_path}"
        # For localhost or when no host header, return relative URL
        return invite_path

    except Exception as e:
        logger.warning("Failed to generate invitation URL: %s", str(e))
        # Fallback to basic format
        return f"/j/{code}"


def _calculate_invitation_status(invitation):
    """Calculate the current status of an invitation based on its fields."""
    from datetime import UTC, datetime

    if invitation.used:
        return "used"

    # Check if invitation has expired
    if invitation.expires:
        # Handle timezone-aware/naive datetime comparison
        now = datetime.now(UTC)
        expires = invitation.expires

        # If expires is naive, assume it's UTC
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=UTC)

        if expires <= now:
            return "expired"

    # Otherwise it's pending
    return "pending"


@status_ns.route("")
class StatusResource(Resource):
    @api.doc("get_status", security="apikey")
    @api.marshal_with(status_model)
    @api.response(401, "Invalid or missing API key", error_model)
    @api.response(500, "Internal server error", error_model)
    @require_api_key
    def get(self):
        """Get overall statistics about your Wizarr instance."""
        try:
            logger.info("API: Getting system status")

            # Get statistics
            from datetime import UTC, datetime

            total_users = User.query.count()
            total_invitations = Invitation.query.count()

            # Calculate pending invitations: not used and (no expiry or not expired yet)
            now = datetime.now(UTC)

            # Get all unused invitations to check their status properly
            all_invitations = Invitation.query.filter(Invitation.used.is_(False)).all()
            pending_invitations = 0
            expired_invitations = 0

            for invitation in all_invitations:
                if invitation.expires is None:
                    pending_invitations += 1
                else:
                    expires = invitation.expires
                    # Handle timezone-naive datetime
                    if expires.tzinfo is None:
                        expires = expires.replace(tzinfo=UTC)

                    if expires > now:
                        pending_invitations += 1
                    else:
                        expired_invitations += 1

            return {
                "users": total_users,
                "invites": total_invitations,
                "pending": pending_invitations,
                "expired": expired_invitations,
            }
        except Exception as e:
            logger.error("Error getting system status: %s", str(e))
            logger.error(traceback.format_exc())
            return {"error": "Internal server error"}, 500


@users_ns.route("")
class UsersListResource(Resource):
    @api.doc("list_users", security="apikey")
    @api.marshal_with(user_list_model)
    @api.response(401, "Invalid or missing API key", error_model)
    @api.response(500, "Internal server error", error_model)
    @require_api_key
    def get(self):
        """List all users across all media servers."""
        try:
            logger.info("API: Listing all users")
            users_by_server = list_users_all_servers()

            # Format response
            users_list = []
            for server_id, users in users_by_server.items():
                # Get server info
                server = db.session.get(MediaServer, server_id)
                if not server:
                    continue

                for user in users:
                    users_list.append(
                        {
                            "id": user.id,
                            "username": user.username,
                            "email": user.email,
                            "server": server.name,
                            "server_type": server.server_type,
                            "expires": user.expires.isoformat()
                            if user.expires
                            else None,
                            "created": user.created.isoformat()
                            if hasattr(user, "created") and user.created
                            else None,
                        }
                    )

            return {"users": users_list, "count": len(users_list)}

        except Exception as e:
            logger.error("Error listing users: %s", str(e))
            logger.error(traceback.format_exc())
            return {"error": "Internal server error"}, 500


@users_ns.route("/<int:user_id>")
class UserResource(Resource):
    @api.doc("delete_user", security="apikey")
    @api.response(200, "User deleted successfully", success_message_model)
    @api.response(401, "Invalid or missing API key", error_model)
    @api.response(404, "User not found", error_model)
    @api.response(500, "Internal server error", error_model)
    @require_api_key
    def delete(self, user_id):
        """Delete a specific user by ID."""
        # Find user first, outside try block
        user = db.session.get(User, user_id)
        if not user:
            abort(404, error="User not found")

        # Get server info for the user
        server = db.session.get(MediaServer, user.server_id)
        if not server:
            abort(404, error="Server not found for user")

        try:
            logger.info("API: Deleting user %s", user_id)

            # Delete user using the service (takes only user.id)
            delete_user(user.id)
            return {"message": f"User {user.username} deleted successfully"}

        except Exception as e:
            logger.error("Error deleting user %s: %s", user_id, str(e))
            logger.error(traceback.format_exc())
            return {"error": "Internal server error"}, 500


@users_ns.route("/<int:user_id>/extend")
class UserExtendResource(Resource):
    @api.doc("extend_user_expiry", security="apikey")
    @api.expect(user_extend_request)
    @api.marshal_with(user_extend_response)
    @api.response(401, "Invalid or missing API key", error_model)
    @api.response(404, "User not found", error_model)
    @api.response(500, "Internal server error", error_model)
    @require_api_key
    def post(self, user_id):
        """Extend a user's expiry date."""
        # Find user first, outside try block to allow abort to work properly
        user = db.session.get(User, user_id)
        if not user:
            abort(404, error="User not found")

        try:
            logger.info("API: Extending expiry for user %s", user_id)

            # Get request data
            data = api.payload or {}
            days = data.get("days", 30)

            # Extend expiry
            if user.expires:
                new_expiry = user.expires + datetime.timedelta(days=days)
            else:
                new_expiry = datetime.datetime.now(datetime.UTC) + datetime.timedelta(
                    days=days
                )

            user.expires = new_expiry
            db.session.commit()

            return {
                "message": f"User {user.username} expiry extended by {days} days",
                "new_expiry": new_expiry.isoformat(),
            }

        except Exception as e:
            logger.error("Error extending user %s expiry: %s", user_id, str(e))
            logger.error(traceback.format_exc())
            return {"error": "Internal server error"}, 500


@invitations_ns.route("")
class InvitationsListResource(Resource):
    @api.doc("list_invitations", security="apikey")
    @api.marshal_with(invitation_list_model)
    @api.response(401, "Invalid or missing API key", error_model)
    @api.response(500, "Internal server error", error_model)
    @require_api_key
    def get(self):
        """List all invitations with their current status and server information."""
        try:
            logger.info("API: Listing all invitations")

            invitations = Invitation.query.all()
            invitations_list = []

            for invitation in invitations:
                # Get servers associated with the invitation
                servers = []

                # Check new multi-server relationship first
                if invitation.servers:
                    servers = invitation.servers
                # Fall back to legacy single server field
                elif invitation.server_id:
                    server = db.session.get(MediaServer, invitation.server_id)
                    if server:
                        servers = [server]

                # Use server name resolver for display name logic
                display_info = get_display_name_info(servers)

                # Convert specific_libraries from string to list of integers
                specific_libraries = []
                if invitation.specific_libraries:
                    try:
                        # Parse comma-separated string to list of integers
                        specific_libraries = [
                            int(lib_id.strip())
                            for lib_id in invitation.specific_libraries.split(",")
                            if lib_id.strip().isdigit()
                        ]
                    except (ValueError, AttributeError):
                        # If parsing fails, use empty list
                        specific_libraries = []

                invitations_list.append(
                    {
                        "id": invitation.id,
                        "code": invitation.code,
                        "url": _generate_invitation_url(invitation.code),
                        "status": _calculate_invitation_status(invitation),
                        "created": invitation.created.isoformat()
                        if invitation.created
                        else None,
                        "expires": invitation.expires.isoformat()
                        if invitation.expires
                        else None,
                        "used_at": invitation.used_at.isoformat()
                        if invitation.used_at
                        else None,
                        "used_by": invitation.used_by,
                        "duration": str(invitation.duration)
                        if invitation.duration
                        else "unlimited",
                        "unlimited": invitation.unlimited,
                        "specific_libraries": specific_libraries,
                        "display_name": display_info["display_name"],
                        "server_names": display_info["server_names"],
                        "uses_global_setting": display_info["uses_global_setting"],
                    }
                )

            return {"invitations": invitations_list, "count": len(invitations_list)}

        except Exception as e:
            logger.error("Error listing invitations: %s", str(e))
            logger.error(traceback.format_exc())
            return {"error": "Internal server error"}, 500

    @api.doc("create_invitation", security="apikey")
    @api.expect(invitation_create_request)
    @api.response(201, "Invitation created successfully", invitation_create_response)
    @api.response(400, "Bad request - missing required fields", error_model)
    @api.response(401, "Invalid or missing API key", error_model)
    @api.response(500, "Internal server error", error_model)
    @require_api_key
    def post(self):
        """Create a new invitation."""
        try:
            logger.info("API: Creating new invitation")

            data = api.payload or {}
            server_ids = data.get("server_ids")

            if not server_ids:
                # Return available servers for selection
                servers = MediaServer.query.filter_by(verified=True).all()
                available_servers = [
                    {"id": s.id, "name": s.name, "server_type": s.server_type}
                    for s in servers
                ]
                # Return error response without marshalling
                response_data = {
                    "error": "Server selection is required. Please specify server_ids in request.",
                    "available_servers": available_servers,
                }
                from flask import jsonify, make_response

                return make_response(jsonify(response_data), 400)

            # Validate that all server IDs exist and are verified
            servers = MediaServer.query.filter(
                MediaServer.id.in_(server_ids), MediaServer.verified
            ).all()

            found_server_ids = {s.id for s in servers}
            invalid_ids = [sid for sid in server_ids if sid not in found_server_ids]

            if invalid_ids:
                from flask import jsonify, make_response

                response_data = {
                    "error": f"Server IDs {invalid_ids} not found or not verified"
                }
                return make_response(jsonify(response_data), 400)

            # Create a form-like object that create_invite expects
            class FormLike:
                def __init__(self, data):
                    self.data = data

                def get(self, key, default=None):
                    return self.data.get(key, default)

                def getlist(self, key):
                    val = self.data.get(key, [])
                    return (
                        val
                        if isinstance(val, list)
                        else [val]
                        if val is not None
                        else []
                    )

            # Map expires_in_days to the format expected by create_invite
            expires_mapping = {1: "day", 7: "week", 30: "month"}
            expires_key = expires_mapping.get(data.get("expires_in_days"), "never")

            form_data = FormLike(
                {
                    "server_ids": server_ids,
                    "expires": expires_key,
                    "duration": data.get("duration", "unlimited"),
                    "unlimited": data.get("unlimited", True),
                    "libraries": [
                        str(lid) for lid in data.get("library_ids", [])
                    ],  # Convert to strings
                    "allow_downloads": data.get("allow_downloads", False),
                    "allow_live_tv": data.get("allow_live_tv", False),
                    "allow_mobile_uploads": data.get("allow_mobile_uploads", False),
                }
            )

            invitation = create_invite(form_data)

            if invitation:
                server = db.session.get(MediaServer, server_ids[0])
                return {
                    "message": "Invitation created successfully",
                    "invitation": {
                        "id": invitation.id,
                        "code": invitation.code,
                        "url": _generate_invitation_url(invitation.code),
                        "expires": invitation.expires.isoformat()
                        if invitation.expires
                        else None,
                        "duration": str(invitation.duration)
                        if invitation.duration
                        else "unlimited",
                        "unlimited": invitation.unlimited,
                        "display_name": server.name if server else "Unknown",
                        "server_names": [server.name] if server else [],
                        "uses_global_setting": False,
                    },
                }, 201
            from flask import jsonify, make_response

            return make_response(jsonify({"error": "Failed to create invitation"}), 500)

        except Exception as e:
            logger.error("Error creating invitation: %s", str(e))
            logger.error(traceback.format_exc())
            from flask import jsonify, make_response

            return make_response(jsonify({"error": "Internal server error"}), 500)


@invitations_ns.route("/<int:invitation_id>")
class InvitationResource(Resource):
    @api.doc("delete_invitation", security="apikey")
    @api.response(200, "Invitation deleted successfully", success_message_model)
    @api.response(401, "Invalid or missing API key", error_model)
    @api.response(404, "Invitation not found", error_model)
    @api.response(500, "Internal server error", error_model)
    @require_api_key
    def delete(self, invitation_id):
        """Delete a specific invitation."""
        # Find invitation first, outside try block
        invitation = db.session.get(Invitation, invitation_id)
        if not invitation:
            abort(404, error="Invitation not found")

        try:
            logger.info("API: Deleting invitation %s", invitation_id)

            code = invitation.code
            db.session.delete(invitation)
            db.session.commit()

            return {"message": f"Invitation {code} deleted successfully"}

        except Exception as e:
            logger.error("Error deleting invitation %s: %s", invitation_id, str(e))
            logger.error(traceback.format_exc())
            return {"error": "Internal server error"}, 500


@libraries_ns.route("")
class LibrariesResource(Resource):
    @api.doc("list_libraries", security="apikey")
    @api.marshal_with(library_list_model)
    @api.response(401, "Invalid or missing API key", error_model)
    @api.response(500, "Internal server error", error_model)
    @require_api_key
    def get(self):
        """List all available libraries across all servers."""
        try:
            logger.info("API: Listing all libraries")

            libraries = Library.query.all()

            # If no libraries exist, scan all servers to populate them
            if not libraries:
                logger.info("No libraries found, scanning all verified servers")
                servers = MediaServer.query.filter_by(verified=True).all()
                for server in servers:
                    try:
                        logger.info(f"Scanning libraries for server {server.name}")
                        from app.services.media.service import scan_libraries_for_server

                        library_data = scan_libraries_for_server(server)

                        # Create Library records for each scanned library
                        for external_id, name in library_data.items():
                            # Check if library already exists to avoid duplicates
                            existing = Library.query.filter_by(
                                external_id=external_id, server_id=server.id
                            ).first()

                            if not existing:
                                library = Library(
                                    external_id=external_id,
                                    name=name,
                                    server_id=server.id,
                                    enabled=True,
                                )
                                db.session.add(library)

                        db.session.commit()
                        logger.info(
                            f"Added {len(library_data)} libraries for server {server.name}"
                        )

                    except Exception as e:
                        logger.error(
                            f"Failed to scan libraries for server {server.name}: {str(e)}"
                        )
                        # Continue with other servers even if one fails
                        continue

                # Re-query libraries after scanning
                libraries = Library.query.all()

            libraries_list = []

            for lib in libraries:
                # Get server name
                server = (
                    db.session.get(MediaServer, lib.server_id)
                    if lib.server_id
                    else None
                )
                server_name = server.name if server else "Unknown"

                libraries_list.append(
                    {
                        "id": lib.id,
                        "name": lib.name,
                        "external_id": lib.external_id,
                        "server_id": lib.server_id,
                        "server_name": server_name,
                        "enabled": lib.enabled,
                    }
                )

            return {"libraries": libraries_list, "count": len(libraries_list)}

        except Exception as e:
            logger.error("Error listing libraries: %s", str(e))
            logger.error(traceback.format_exc())
            return {"error": "Internal server error"}, 500


@servers_ns.route("")
class ServersResource(Resource):
    @api.doc("list_servers", security="apikey")
    @api.marshal_with(server_list_model)
    @api.response(401, "Invalid or missing API key", error_model)
    @api.response(500, "Internal server error", error_model)
    @require_api_key
    def get(self):
        """List all configured media servers."""
        try:
            logger.info("API: Listing all servers")

            servers = MediaServer.query.all()
            servers_list = [
                {
                    "id": server.id,
                    "name": server.name,
                    "server_type": server.server_type,
                    "server_url": server.url,
                    "external_url": getattr(server, "external_url", None),
                    "verified": server.verified,
                    "allow_downloads": getattr(server, "allow_downloads", False),
                    "allow_live_tv": getattr(server, "allow_live_tv", False),
                    "allow_mobile_uploads": getattr(
                        server, "allow_mobile_uploads", False
                    ),
                    "created_at": server.created_at.isoformat()
                    if hasattr(server, "created_at") and server.created_at
                    else None,
                }
                for server in servers
            ]

            return {"servers": servers_list, "count": len(servers_list)}

        except Exception as e:
            logger.error("Error listing servers: %s", str(e))
            logger.error(traceback.format_exc())
            return {"error": "Internal server error"}, 500


@api_keys_ns.route("")
class ApiKeysResource(Resource):
    @api.doc("list_api_keys", security="apikey")
    @api.marshal_with(api_key_list_model)
    @api.response(401, "Invalid or missing API key", error_model)
    @api.response(500, "Internal server error", error_model)
    @require_api_key
    def get(self):
        """List all active API keys (excluding the actual key values for security)."""
        try:
            logger.info("API: Listing all API keys")

            api_keys = ApiKey.query.filter_by(is_active=True).all()
            keys_list = [
                {
                    "id": key.id,
                    "name": key.name,
                    "created_at": key.created_at.isoformat()
                    if key.created_at
                    else None,
                    "last_used_at": key.last_used_at.isoformat()
                    if key.last_used_at
                    else None,
                    "created_by": getattr(key, "created_by", "admin"),
                }
                for key in api_keys
            ]

            return {"api_keys": keys_list, "count": len(keys_list)}

        except Exception as e:
            logger.error("Error listing API keys: %s", str(e))
            logger.error(traceback.format_exc())
            return {"error": "Internal server error"}, 500


@api_keys_ns.route("/<int:key_id>")
class ApiKeyResource(Resource):
    @api.doc("delete_api_key", security="apikey")
    @api.response(200, "API key deleted successfully", success_message_model)
    @api.response(401, "Invalid or missing API key", error_model)
    @api.response(404, "API key not found", error_model)
    @api.response(500, "Internal server error", error_model)
    @require_api_key
    def delete(self, key_id):
        """Delete a specific API key (soft delete - marks as inactive)."""
        # Find API key first, outside try block
        api_key = db.session.get(ApiKey, key_id)
        if not api_key:
            abort(404, error="API key not found")

        try:
            logger.info("API: Deleting API key %s", key_id)

            # Check if trying to delete the currently used key
            auth_key = request.headers.get("X-API-Key")
            if auth_key:
                current_key_hash = hashlib.sha256(auth_key.encode()).hexdigest()
                if api_key.key_hash == current_key_hash:
                    return {
                        "error": "Cannot delete the API key currently being used"
                    }, 400

            key_name = api_key.name
            api_key.is_active = False
            db.session.commit()

            return {"message": f"API key '{key_name}' deleted successfully"}

        except Exception as e:
            logger.error("Error deleting API key %s: %s", key_id, str(e))
            logger.error(traceback.format_exc())
            return {"error": "Internal server error"}, 500
