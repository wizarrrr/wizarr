import datetime
import hashlib
import logging
import traceback
from functools import wraps

from flask import Blueprint, jsonify, request, url_for

from app.extensions import db
from app.models import ApiKey, Invitation, Library, MediaServer, User
from app.services.invites import create_invite
from app.services.media.service import delete_user, list_users_all_servers

api_bp = Blueprint("api", __name__, url_prefix="/api")

# Set up logging for API
logger = logging.getLogger("wizarr.api")


def _generate_invitation_url(code):
    """Generate full invitation URL for the given code."""
    try:
        # Try to generate URL using url_for with the public blueprint's invite route
        invite_path = url_for('public.invite', code=code, _external=False)
        
        # Get the host from the current request if available
        host = request.headers.get('Host')
        if host and not host.startswith('localhost'):
            # Only generate full URL for non-localhost hosts
            scheme = 'https' if request.headers.get('X-Forwarded-Proto') == 'https' or request.is_secure else 'http'
            full_url = f"{scheme}://{host}{invite_path}"
            return full_url
        else:
            # For localhost or when no host header, return relative URL
            return invite_path
            
    except Exception as e:
        logger.warning("Failed to generate invitation URL: %s", str(e))
        # Fallback to basic format
        return f"/j/{code}"


def require_api_key(f):
    """Decorator to require valid API key for endpoint access."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_key = request.headers.get("X-API-Key")
        if not auth_key:
            logger.warning("API request without API key from %s", request.remote_addr)
            return jsonify({"error": "API key required"}), 401

        # Hash the provided key to compare with stored hash
        key_hash = hashlib.sha256(auth_key.encode()).hexdigest()
        api_key = ApiKey.query.filter_by(key_hash=key_hash, is_active=True).first()

        if not api_key:
            logger.warning("API request with invalid API key from %s", request.remote_addr)
            return jsonify({"error": "Invalid API key"}), 401

        # Update last used timestamp
        api_key.last_used_at = datetime.datetime.now(datetime.UTC)
        db.session.commit()

        logger.info("API request authenticated with key '%s' from %s", api_key.name, request.remote_addr)
        return f(*args, **kwargs)

    return decorated_function


@api_bp.route("/users", methods=["GET"])
@require_api_key
def list_users():
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
                users_list.append({
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "server": server.name,
                    "server_type": server.server_type,
                    "expires": user.expires.isoformat() if user.expires else None,
                    "created": user.created.isoformat() if hasattr(user, 'created') and user.created else None
                })

        return jsonify({"users": users_list, "count": len(users_list)})

    except Exception as e:
        logger.error("Error listing users: %s", str(e))
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@api_bp.route("/users/<int:user_id>", methods=["DELETE"])
@require_api_key
def delete_user_endpoint(user_id):
    """Delete a user by ID."""
    try:
        user = db.session.get(User, user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404

        logger.info("API: Deleting user %s (ID: %d)", user.username, user_id)
        result = delete_user(user.server_id, user.token)

        if result:
            return jsonify({"message": f"User {user.username} deleted successfully"})
        return jsonify({"error": "Failed to delete user"}), 500

    except Exception as e:
        logger.error("Error deleting user %d: %s", user_id, str(e))
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@api_bp.route("/users/<int:user_id>/extend", methods=["POST"])
@require_api_key
def extend_user_expiry(user_id):
    """Extend user expiry date."""
    try:
        user = db.session.get(User, user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404

        data = request.get_json() or {}
        days = data.get("days", 30)  # Default to 30 days

        if user.expires:
            new_expiry = user.expires + datetime.timedelta(days=days)
        else:
            new_expiry = datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=days)

        user.expires = new_expiry
        db.session.commit()

        logger.info("API: Extended user %s expiry by %d days to %s", user.username, days, new_expiry)
        return jsonify({
            "message": f"User {user.username} expiry extended by {days} days",
            "new_expiry": new_expiry.isoformat()
        })

    except Exception as e:
        logger.error("Error extending user %d expiry: %s", user_id, str(e))
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@api_bp.route("/invitations", methods=["GET"])
@require_api_key
def list_invitations():
    """List all invitations."""
    try:
        logger.info("API: Listing all invitations")
        now = datetime.datetime.now(datetime.UTC)

        invitations = Invitation.query.all()
        invites_list = []

        for invite in invitations:
            # Determine status
            if invite.used:
                status = "used"
            elif invite.expires:
                # Handle timezone comparison
                invite_expires = invite.expires
                if invite_expires.tzinfo is None:
                    # If invitation expires is naive, assume UTC
                    invite_expires = invite_expires.replace(tzinfo=datetime.UTC)
                status = "expired" if invite_expires < now else "pending"
            else:
                status = "pending"

            # Get server information for this invitation
            from app.services.server_name_resolver import get_display_name_info
            
            servers = []
            if invite.servers:
                servers = list(invite.servers)
            elif invite.server:
                servers = [invite.server]
            
            display_info = get_display_name_info(servers)

            invites_list.append({
                "id": invite.id,
                "code": invite.code,
                "url": _generate_invitation_url(invite.code),
                "status": status,
                "created": invite.created.isoformat() if invite.created else None,
                "expires": invite.expires.isoformat() if invite.expires else None,
                "used_at": invite.used_at.isoformat() if invite.used_at else None,
                "used_by": invite.used_by.username if invite.used_by else None,
                "duration": invite.duration,
                "unlimited": invite.unlimited,
                "specific_libraries": invite.specific_libraries,
                "display_name": display_info["display_name"],
                "server_names": display_info["server_names"],
                "uses_global_setting": display_info["uses_global_setting"]
            })

        return jsonify({"invitations": invites_list, "count": len(invites_list)})

    except Exception as e:
        logger.error("Error listing invitations: %s", str(e))
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@api_bp.route("/invitations", methods=["POST"])
@require_api_key
def create_invitation():
    """Create a new invitation."""
    try:
        # Try to get JSON data, handle missing Content-Type gracefully
        try:
            data = request.get_json() or {}
        except Exception:
            # If JSON parsing fails due to Content-Type, try force parsing
            try:
                data = request.get_json(force=True) or {}
            except Exception:
                data = {}

        # Extract parameters
        expires_in_days = data.get("expires_in_days")
        duration = data.get("duration", "unlimited")
        library_ids = data.get("library_ids", [])
        unlimited = data.get("unlimited", True)
        server_ids = data.get("server_ids", [])  # Allow explicit server specification

        # Map expires_in_days to the expected format
        expires_key = "never"
        if expires_in_days == 1:
            expires_key = "day"
        elif expires_in_days == 7:
            expires_key = "week"
        elif expires_in_days == 30:
            expires_key = "month"

        # Handle server selection logic - server_ids are now required
        if not server_ids:
            # No server IDs specified - this is now always an error
            verified_servers = MediaServer.query.filter_by(verified=True).all()
            available_servers = [
                {"id": s.id, "name": s.name, "server_type": s.server_type}
                for s in verified_servers
            ]
            return jsonify({
                "error": "Server selection is required. Please specify server_ids in request.",
                "available_servers": available_servers
            }), 400
        
        # Server IDs explicitly provided - validate them
        servers = MediaServer.query.filter(
            MediaServer.id.in_(server_ids),
            MediaServer.verified
        ).all()
        if len(servers) != len(server_ids):
            return jsonify({"error": "One or more specified servers not found or not verified"}), 400
        selected_server_ids = server_ids

        # Create a form-like object
        form_data = {
            "duration": duration,
            "expires": expires_key,
            "unlimited": unlimited,
            "server_ids": selected_server_ids,
            "libraries": [str(lib_id) for lib_id in library_ids],
            "allow_downloads": data.get("allow_downloads", False),
            "allow_live_tv": data.get("allow_live_tv", False),
            "allow_mobile_uploads": data.get("allow_mobile_uploads", False),
        }

        # Create a dict-like object that supports both get() and getlist()
        class FormLikeDict(dict):
            def getlist(self, key):
                value = self.get(key, [])
                if isinstance(value, list):
                    return value
                return [value] if value else []

        form_obj = FormLikeDict(form_data)

        # Create the invitation
        logger.info("API: Creating invitation with duration=%s, expires=%s, libraries=%s, servers=%s",
                   duration, expires_key, library_ids, selected_server_ids)

        invitation = create_invite(form_obj)
        db.session.commit()

        # Get server information for the created invitation
        from app.services.server_name_resolver import get_display_name_info
        
        servers = []
        if invitation.servers:
            servers = list(invitation.servers)
        elif invitation.server:
            servers = [invitation.server]
        
        display_info = get_display_name_info(servers)

        return jsonify({
            "message": "Invitation created successfully",
            "invitation": {
                "id": invitation.id,
                "code": invitation.code,
                "url": _generate_invitation_url(invitation.code),
                "expires": invitation.expires.isoformat() if invitation.expires else None,
                "duration": invitation.duration,
                "unlimited": invitation.unlimited,
                "display_name": display_info["display_name"],
                "server_names": display_info["server_names"],
                "uses_global_setting": display_info["uses_global_setting"]
            }
        }), 201

    except Exception as e:
        logger.error("Error creating invitation: %s", str(e))
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@api_bp.route("/invitations/<int:invitation_id>", methods=["DELETE"])
@require_api_key
def delete_invitation(invitation_id):
    """Delete an invitation."""
    try:
        invitation = db.session.get(Invitation, invitation_id)
        if not invitation:
            return jsonify({"error": "Invitation not found"}), 404

        logger.info("API: Deleting invitation %s (ID: %d)", invitation.code, invitation_id)
        db.session.delete(invitation)
        db.session.commit()

        return jsonify({"message": f"Invitation {invitation.code} deleted successfully"})

    except Exception as e:
        logger.error("Error deleting invitation %d: %s", invitation_id, str(e))
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@api_bp.route("/libraries", methods=["GET"])
@require_api_key
def list_libraries():
    """List all available libraries, scanning servers first if needed."""
    try:
        logger.info("API: Listing all libraries")

        # Get all configured servers
        servers = MediaServer.query.filter_by(verified=True).all()

        # Check if we need to scan libraries (if no libraries exist for verified servers)
        existing_libraries = Library.query.join(MediaServer).filter(MediaServer.verified).count()

        if existing_libraries == 0 and servers:
            # No libraries found, scan all verified servers first
            logger.info("API: No libraries found, scanning all verified servers first")
            from app.services.media.service import scan_libraries_for_server

            for server in servers:
                try:
                    logger.info("API: Scanning libraries for server %s", server.name)
                    items = scan_libraries_for_server(server)

                    # Store the results in the Library table
                    # items may be dict or list[str]
                    pairs = (
                        items.items() if isinstance(items, dict) else [(name, name) for name in items]
                    )

                    for fid, name in pairs:
                        lib = Library.query.filter_by(external_id=fid, server_id=server.id).first()
                        if lib:
                            lib.name = name
                        else:
                            lib = Library()
                            lib.external_id = fid
                            lib.name = name
                            lib.server_id = server.id
                            db.session.add(lib)

                    db.session.commit()
                    logger.info("API: Successfully scanned %d libraries for server %s", len(pairs), server.name)

                except Exception as scan_e:
                    logger.warning("API: Failed to scan libraries for server %s: %s", server.name, str(scan_e))
                    # Continue with other servers even if one fails
                    continue

        # Now get all libraries
        libraries = Library.query.all()

        libraries_list = []
        for lib in libraries:
            server = db.session.get(MediaServer, lib.server_id)
            libraries_list.append({
                "id": lib.id,
                "name": lib.name,
                "server_id": lib.server_id,
                "server_name": server.name if server else None,
                "server_type": server.server_type if server else None
            })

        return jsonify({"libraries": libraries_list, "count": len(libraries_list)})

    except Exception as e:
        logger.error("Error listing libraries: %s", str(e))
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@api_bp.route("/servers", methods=["GET"])
@require_api_key
def list_servers():
    """List all configured media servers."""
    try:
        logger.info("API: Listing all media servers")
        servers = MediaServer.query.all()

        servers_list = []
        for server in servers:
            servers_list.append({
                "id": server.id,
                "name": server.name,
                "server_type": server.server_type,
                "server_url": server.url,
                "external_url": server.external_url,
                "verified": server.verified,
                "allow_downloads": server.allow_downloads,
                "allow_live_tv": server.allow_live_tv,
                "allow_mobile_uploads": server.allow_mobile_uploads,
                "created_at": server.created_at.isoformat() if server.created_at else None
            })

        return jsonify({"servers": servers_list, "count": len(servers_list)})

    except Exception as e:
        logger.error("Error listing servers: %s", str(e))
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@api_bp.route("/api-keys", methods=["GET"])
@require_api_key
def list_api_keys():
    """List all active API keys (excluding the key values themselves)."""
    try:
        logger.info("API: Listing all API keys")
        api_keys = ApiKey.query.filter_by(is_active=True).order_by(ApiKey.created_at.desc()).all()

        keys_list = []
        for key in api_keys:
            keys_list.append({
                "id": key.id,
                "name": key.name,
                "created_at": key.created_at.isoformat() if key.created_at else None,
                "last_used_at": key.last_used_at.isoformat() if key.last_used_at else None,
                "created_by": key.created_by.username if key.created_by else None
            })

        return jsonify({"api_keys": keys_list, "count": len(keys_list)})

    except Exception as e:
        logger.error("Error listing API keys: %s", str(e))
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@api_bp.route("/api-keys/<int:key_id>", methods=["DELETE"])
@require_api_key
def delete_api_key_via_api(key_id):
    """Delete an API key via API (soft delete by marking as inactive)."""
    try:
        api_key = db.session.get(ApiKey, key_id)
        if not api_key:
            return jsonify({"error": "API key not found"}), 404

        # Prevent self-deletion by checking if the current request is using this key
        auth_key = request.headers.get("X-API-Key")
        if auth_key:
            key_hash = hashlib.sha256(auth_key.encode()).hexdigest()
            if key_hash == api_key.key_hash:
                return jsonify({"error": "Cannot delete the API key currently being used"}), 400

        # Soft delete by marking as inactive
        api_key.is_active = False
        db.session.commit()

        logger.info("API: Deleted API key '%s' (ID: %d)", api_key.name, key_id)

        return jsonify({"message": f"API key '{api_key.name}' deleted successfully"})

    except Exception as e:
        logger.error("Error deleting API key %d: %s", key_id, str(e))
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
