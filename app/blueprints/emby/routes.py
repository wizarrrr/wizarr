from flask import Blueprint, request, jsonify, abort, render_template, redirect
from flask_login import login_required
from app.services.media.emby import EmbyClient
import logging

# Create an Emby version of the join function similar to Jellyfin
from app.services.invites import is_invite_valid, _mark_invite_used
from app.models import User, Invitation
from app.extensions import db
import re

# Reuse the same email regex as jellyfin
EMAIL_RE = re.compile(r"[^@]+@[^@]+\.[^@]+")

emby_bp = Blueprint("emby", __name__, url_prefix="/emby")

# Ajax scan with arbitrary creds
@emby_bp.route("/scan", methods=["POST"])
@login_required
def scan():
    client = EmbyClient()
    url = request.args.get("emby_url")
    key = request.args.get("emby_api_key")
    if not url or not key:
        abort(400)
    try:
        libs = client.libraries()
        return jsonify(libs)
    except Exception as e:
        logging.error(f"Error scanning Emby libraries: {str(e)}")
        abort(400)

# Scan with saved creds
@emby_bp.route("/scan-specific", methods=["POST"])
@login_required
def scan_specific():
    client = EmbyClient()
    return jsonify(client.libraries())

# Define the join function for Emby users
def join(username: str, password: str, confirm: str, email: str, code: str) -> tuple[bool, str]:
    client = EmbyClient()
    
    # Validate input data
    if not EMAIL_RE.fullmatch(email):
        return False, "Invalid e-mail address."
    if not 8 <= len(password) <= 20:
        return False, "Password must be 8–20 characters."
    if password != confirm:
        return False, "Passwords do not match."
    
    # Validate invitation code
    ok, msg = is_invite_valid(code)
    if not ok:
        return False, msg
    
    # Get invitation record
    inv = Invitation.query.filter_by(code=code).first()
    
    try:
        # Create the user in Emby
        logging.info(f"Creating Emby user: {username}")
        
        # Step 1: Create the user in Emby
        user_id = client.create_user(username, password)
        logging.info(f"Emby user created with ID: {user_id}")
        
        # Step 2: Set user policy based on invitation settings
        policy = {
            "IsAdministrator": False,
            "IsHidden": False,
            "IsDisabled": False,
            "EnableUserPreferenceAccess": True,
            "AccessSchedules": [],
            "BlockedTags": [],
            "EnableRemoteControlOfOtherUsers": False,
            "EnableSharedDeviceControl": False,
            "EnableRemoteAccess": True,
            "EnableLiveTvManagement": False,
            "EnableLiveTvAccess": True,
            "EnableMediaPlayback": True,
            "EnableAudioPlaybackTranscoding": True,
            "EnableVideoPlaybackTranscoding": True,
            "EnablePlaybackRemuxing": True,
            "EnableContentDeletion": False,
            "EnableContentDownloading": True,
            "EnableSubtitleDownloading": True,
            "EnableSubtitleManagement": True,
            "EnableSyncTranscoding": True,
            "EnableMediaConversion": True,
            "EnableAllDevices": True,
        }
        
        # Apply the policy to the user
        client.set_policy(user_id, policy)
        logging.info(f"Applied policy for Emby user: {username}")
        
        # Get user expiry from invitation
        if inv.expires_val == "week":
            expires = 7
        elif inv.expires_val == "month":
            expires = 30
        else:
            expires = None
        
        # Create local user record
        new_user = User(
            username=username,
            email=email,
            password="emby-user",  # Not used for auth, just a placeholder
            token=user_id,
            code=code,
            expires=expires,
        )
        
        db.session.add(new_user)
        db.session.commit()
        
        # Mark invitation as used
        _mark_invite_used(inv, new_user)
        
        # Return success
        return True, ""
        
    except Exception as e:
        logging.error(f"Emby join error: {str(e)}", exc_info=True)
        db.session.rollback()
        return False, "An unexpected error occurred during user creation."

# Public join endpoint called from the wizard form
@emby_bp.route("/join", methods=["POST"])
def public_join():
    ok, msg = join(
        username = request.form["username"],
        password = request.form["password"],
        confirm  = request.form["confirm-password"],
        email    = request.form["email"],
        code     = request.form["code"],
    )
    if ok:
        return redirect("/wizard/")
    return render_template("welcome-jellyfin.html",
                          username=request.form["username"],
                          email=request.form["email"],
                          code=request.form["code"],
                          error=msg)
