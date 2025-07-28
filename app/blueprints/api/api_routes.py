import datetime
import hashlib
import logging
import secrets
import traceback
from functools import wraps

from flask import Blueprint, jsonify, request
from flask_login import current_user

from app.extensions import db
from app.models import ApiKey, Invitation, Library, MediaServer, User
from app.services.invites import create_invite
from app.services.media.service import delete_user, list_users_all_servers

api_bp = Blueprint("api", __name__, url_prefix="/api")

# Set up logging for API
logger = logging.getLogger("wizarr.api")


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
        users_data = list_users_all_servers()
        
        # Format response
        users_list = []
        for server_data in users_data:
            for user in server_data.get("users", []):
                users_list.append({
                    "id": user.get("id"),
                    "username": user.get("username"),
                    "email": user.get("email"),
                    "server": server_data.get("server_name"),
                    "server_type": server_data.get("server_type"),
                    "expires": user.get("expires"),
                    "created": user.get("created")
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
        user = User.query.get(user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        logger.info("API: Deleting user %s (ID: %d)", user.username, user_id)
        result = delete_user(user.server_id, user.token)
        
        if result:
            return jsonify({"message": f"User {user.username} deleted successfully"})
        else:
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
        user = User.query.get(user_id)
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
            elif invite.expires and invite.expires < now:
                status = "expired" 
            else:
                status = "pending"
            
            invites_list.append({
                "id": invite.id,
                "code": invite.code,
                "status": status,
                "created": invite.created.isoformat() if invite.created else None,
                "expires": invite.expires.isoformat() if invite.expires else None,
                "used_at": invite.used_at.isoformat() if invite.used_at else None,
                "used_by": invite.used_by.username if invite.used_by else None,
                "duration": invite.duration,
                "unlimited": invite.unlimited,
                "specific_libraries": invite.specific_libraries
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
        data = request.get_json() or {}
        
        # Extract parameters
        expires_in_days = data.get("expires_in_days")
        duration = data.get("duration", "unlimited")
        library_ids = data.get("library_ids", [])
        unlimited = data.get("unlimited", True)
        
        # Calculate expiry date
        expires = None
        if expires_in_days:
            expires = datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=expires_in_days)
        
        # Get libraries
        libraries = []
        if library_ids:
            libraries = Library.query.filter(Library.id.in_(library_ids)).all()
        
        # Create the invitation
        logger.info("API: Creating invitation with duration=%s, expires=%s, libraries=%s", 
                   duration, expires, [lib.id for lib in libraries])
        
        invitation = create_invite(
            duration=duration,
            expires=expires,
            libraries=libraries,
            unlimited=unlimited
        )
        
        return jsonify({
            "message": "Invitation created successfully",
            "invitation": {
                "id": invitation.id,
                "code": invitation.code,
                "expires": invitation.expires.isoformat() if invitation.expires else None,
                "duration": invitation.duration,
                "unlimited": invitation.unlimited
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
        invitation = Invitation.query.get(invitation_id)
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
    """List all available libraries."""
    try:
        logger.info("API: Listing all libraries")
        libraries = Library.query.all()
        
        libraries_list = []
        for lib in libraries:
            libraries_list.append({
                "id": lib.id,
                "name": lib.name,
                "server_id": lib.server_id
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
                "server_url": server.server_url
            })
        
        return jsonify({"servers": servers_list, "count": len(servers_list)})
    
    except Exception as e:
        logger.error("Error listing servers: %s", str(e))
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500