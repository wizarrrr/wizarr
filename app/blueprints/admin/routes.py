import logging
from flask import Blueprint, render_template, request, redirect, abort, url_for
from app.services.invites import create_invite
from app.services.media.service import list_users, delete_user
from app.services.update_check import check_update_available, get_sponsors
from app.extensions import db, htmx
from app.models import Invitation, Settings, User
from app.blueprints.settings.routes import _load_settings
import os
from flask_login import login_required
import datetime
from urllib.parse import urlparse

admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/admin")
@login_required
def dashboard():
    __version__ = os.getenv("APP_VERSION", "dev")
    update_available = check_update_available(__version__)
    sponsors = get_sponsors()
    print(sponsors)

    return render_template("admin.html",
                           update_available=update_available,
                           sponsors=sponsors,
                           version=__version__)


# Invitations – landing page
@admin_bp.route("/invite", methods=["GET", "POST"])
@login_required
def invite():
    if not request.headers.get("HX-Request"):
        return redirect(url_for(".dashboard"))

    # Load all settings using the helper function that handles boolean conversion
    settings = _load_settings()
    server_type = settings.get("server_type")
    allow_downloads_plex = settings.get("allow_downloads_plex", False)
    allow_tv_plex = settings.get("allow_tv_plex", False)

    if request.method == "POST":
        try:
            code = request.form.get("code") or None
            invite = create_invite(request.form)
        except ValueError:
            return abort(401)  # duplicate / malformed code

        current_url = request.headers.get('HX-Current-URL')
        parsed_url = urlparse(current_url)
        host_url = f"{parsed_url.scheme}://{parsed_url.netloc}"

        link = f"{host_url}/j/{invite.code}"

        invitations = (
            Invitation.query
            .order_by(Invitation.created.desc())
            .all()
        )
        return render_template(
            "admin/invite.html",
            link=link,
            invitations=invitations,
            server_type=server_type,
            allow_downloads_plex=allow_downloads_plex,
            allow_tv_plex=allow_tv_plex,
        )

    # GET

    return render_template(
        "admin/invite.html",
        server_type=server_type,
        allow_downloads_plex=allow_downloads_plex,
        allow_tv_plex=allow_tv_plex,

    )


# standalone /invites page (shell around HTMX)
@admin_bp.route("/invites")
@login_required
def invites():
    if not request.headers.get("HX-Request"):
        return redirect(url_for(".dashboard"))
    return render_template("admin/invites.html")


# HTMX partial for the table cards
@admin_bp.route("/invite/table", methods=["POST"])
@login_required
def invite_table():
    if (code := request.args.get("delete")):
        (
            Invitation.query
            .filter_by(code=code)
            .delete()
        )
        db.session.commit()

    invites = (
        Invitation.query
        .options(db.joinedload(Invitation.libraries))  # Eager load libraries
        .order_by(Invitation.created.desc())
        .all()
    )
    now = datetime.datetime.now()

    # annotate expiry
    for inv in invites:
        if inv.expires:
            if isinstance(inv.expires, str):
                inv.expires = datetime.datetime.strptime(
                    inv.expires, "%Y-%m-%d %H:%M"
                )
            inv.expired = inv.expires < now

    server_type_setting = (
        Settings.query
        .filter_by(key="server_type")
        .first()
    )
    server_type = server_type_setting.value if server_type_setting else None

    return render_template(
        "tables/invite_card.html",
        server_type=server_type,
        invitations=invites,
        rightnow=now,
    )


# Users
@admin_bp.route("/users")
@login_required
def users():
    return render_template("admin/users.html")  # static shell


@admin_bp.route("/users/table")
@login_required
def users_table():
    if (uid := request.args.get("delete")):
        delete_user(int(uid))

    users = []
    try:
        users = list_users() or []
    except Exception as exc:
        logging.error("Error fetching users: %s", exc)
    return render_template("tables/user_card.html", users=users)


@admin_bp.route("/user/<int:db_id>", methods=["GET", "POST"])
@login_required
def user_detail(db_id: int):
    """
    • GET  → return the small expiry-edit modal
    • POST → update expiry then return the *entire* card grid
    """
    user = User.query.get_or_404(db_id)

    if request.method == "POST":
        raw = request.form.get("expires")  # "" or 2025-05-22T14:00
        user.expires = datetime.datetime.fromisoformat(raw).date() if raw else None
        db.session.commit()

        # Re-render the grid the same way /users/table does

        users = list_users(clear_cache=True)
        return render_template("tables/user_card.html", users=users)

    # ── GET → serve the compact modal ─────────────────────────────
    return render_template("admin/user_modal.html", user=user)
