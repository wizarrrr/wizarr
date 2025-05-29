from flask import Blueprint, request, jsonify, abort, render_template, redirect
from flask_login import login_required
from app.services.media.emby import EmbyClient
import logging
import datetime

# Create an Emby version of the join function similar to Jellyfin
from app.services.invites import is_invite_valid
from app.models import User, Invitation, Library
from app.extensions import db
from sqlalchemy import or_
from app.services.notifications import notify
import re

# Reuse the same email regex as jellyfin
EMAIL_RE = re.compile(r"[^@]+@[^@]+\.[^@]+")

# Define the mark_invite_used function like in jellyfin.py
def _mark_invite_used(inv: Invitation, user: User) -> None:
    inv.used = True if not inv.unlimited else inv.used
    inv.used_at = datetime.datetime.now()
    inv.used_by = user
    db.session.commit()

# Helper function to find folder ID from name
def _folder_name_to_id(name: str, cache: dict[str, str]) -> str | None:
    return cache.get(name)

# Set specific folders for a user
def set_specific_folders(client: EmbyClient, user_id: str, names: list[str]):
    mapping = client.libraries()
    
    folder_ids = [_folder_name_to_id(n, mapping) for n in names]
    folder_ids = [fid for fid in folder_ids if fid]
    
    policy_patch = {
        "EnableAllFolders": not folder_ids,
        "EnabledFolders": folder_ids,
    }
    
    # Get current policy and update it
    user_data = client.get_user(user_id)
    current = user_data.get("Policy", {})
    current.update(policy_patch)
    
    # Apply updated policy
    client.set_policy(user_id, current)

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
        
    # Check for existing users with same username/email
    existing = User.query.filter(
        or_(User.username == username, User.email == email)
    ).first()
    if existing:
        return False, "User or e-mail already exists."
    
    try:
        # Create the user in Emby
        logging.info(f"Creating Emby user: {username}")
        
        # Step 1: Create the user in Emby
        user_id = client.create_user(username, password)
        logging.info(f"Emby user created with ID: {user_id}")
        
        # Get invitation record
        inv = Invitation.query.filter_by(code=code).first()
        
        # Step 2: Set library permissions based on invitation settings
        if inv.libraries:
            sections = [lib.external_id for lib in inv.libraries]
        else:
            sections = [
                lib.external_id
                for lib in Library.query.filter_by(enabled=True).all()
            ]
            
        # Apply folder permissions
        set_specific_folders(client, user_id, sections)
        logging.info(f"Applied library permissions for Emby user: {username}")
        
        # Calculate expiration date if needed
        expires = None
        if inv.duration:
            days = int(inv.duration)
            expires = datetime.datetime.utcnow() + datetime.timedelta(days=days)
        
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
        notify("New User", f"User {username} has joined your Emby server! 🎉", tags="tada")
        
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
                          server_type="emby",
                          error=msg)
