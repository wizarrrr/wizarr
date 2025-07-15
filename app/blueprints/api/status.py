import datetime
import os
import traceback

from flask import Blueprint, jsonify, request

from app.models import Invitation, User

status_bp = Blueprint("status", __name__, url_prefix="/api")

API_KEY = os.environ.get("WIZARR_API_KEY")


@status_bp.route("/status", methods=["GET"])
def status():
    # Require API key and can not be blank or empty space
    auth_key = request.headers.get("X-API-Key")
    if not API_KEY or API_KEY.strip() == "" or not auth_key or auth_key != API_KEY:
        return jsonify({"error": "Unauthorized"}), 401

    try:
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
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
