import datetime
import hashlib
import logging
import traceback

from flask import Blueprint, jsonify, request

from app.extensions import db
from app.models import ApiKey, Invitation, User

status_bp = Blueprint("status", __name__, url_prefix="/api")

# Set up logging for API
logger = logging.getLogger("wizarr.api")


def authenticate_api_key():
    """Check if the provided API key is valid."""
    auth_key = request.headers.get("X-API-Key")
    if not auth_key:
        return False, None

    # Hash the provided key to compare with stored hash
    key_hash = hashlib.sha256(auth_key.encode()).hexdigest()
    api_key = ApiKey.query.filter_by(key_hash=key_hash, is_active=True).first()

    if api_key:
        # Update last used timestamp
        api_key.last_used_at = datetime.datetime.now(datetime.UTC)
        db.session.commit()
        return True, api_key

    return False, None


@status_bp.route("/status", methods=["GET"])
def status():
    # Check new API key system first
    is_authenticated, api_key = authenticate_api_key()

    if not is_authenticated:
        logger.warning(
            "API status request without valid API key from %s", request.remote_addr
        )
        return jsonify({"error": "Unauthorized"}), 401

    try:
        logger.info(
            "API status request authenticated with key '%s' from %s",
            api_key.name if api_key else "unknown",
            request.remote_addr,
        )

        now = datetime.datetime.now()
        # Total users
        users = User.query.count()
        # Total invites
        invites = Invitation.query.count()
        # Pending = not used and not expired
        pending = Invitation.query.filter(
            Invitation.used.is_(False),
            (Invitation.expires.is_(None)) | (Invitation.expires >= now),
        ).count()
        # Expired if invitation time less than now
        expired = Invitation.query.filter(
            Invitation.expires.is_not(None), Invitation.expires < now
        ).count()

        return jsonify(
            {"users": users, "invites": invites, "pending": pending, "expired": expired}
        )

    except Exception as e:
        logger.error("Error in status endpoint: %s", str(e))
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
