import logging
from flask import Blueprint, render_template, request, redirect, abort, url_for
from app.services.invites import create_invite
from app.services.jellyfin_client import JellyfinClient
from app.services.media_service import list_users, delete_user
from app.services.plex_client import PlexClient
from app.utils.auth import builtin_login_required
from app.services import invites as invite_service
from app.services.update_check import needs_update
from app.extensions import db
from app.models import Invitation, Notification, Settings, User
import os
from flask_login import login_required
import datetime

admin_bp = Blueprint("admin", __name__)

@admin_bp.route("/admin")
@login_required
def dashboard():
    server_verified = (
        Settings.query
        .filter_by(key="server_verified")
        .first()
    )
    if not server_verified or server_verified.value != "true":
        return redirect("/setup/")
    return render_template("admin.html")

# Invitations – landing page
@admin_bp.route("/invite", methods=["GET", "POST"])
@login_required
def invite():
    if not request.headers.get("HX-Request"):
        return redirect(url_for(".dashboard"))

    if request.method == "POST":
        try:
            code = request.form.get("code") or None
            invite = create_invite(request.form)
        except ValueError:
            return abort(401)  # duplicate / malformed code

        link = f"{os.getenv('APP_URL')}/j/{invite.code}"
        invitations = (
            Invitation.query
            .order_by(Invitation.created.desc())
            .all()
        )
        return render_template(
            "admin/invite.html",
            link=link,
            invitations=invitations,
            url=os.getenv("APP_URL"),
        )

    # GET
    server_type_setting = (
        Settings.query
        .filter_by(key="server_type")
        .first()
    )
    server_type = server_type_setting.value if server_type_setting else None
    return render_template(
        "admin/invite.html",
        needUpdate=needs_update(),
        url=os.getenv("APP_URL"),
        server_type=server_type,
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
def user_detail(db_id):
    if not request.headers.get("HX-Request"):
        return redirect(url_for(".dashboard"))

    # server type
    server_type_setting = (
        Settings.query
        .filter_by(key="server_type")
        .first()
    )
    server_type = server_type_setting.value if server_type_setting else None

    if server_type == "plex":
        plex = PlexClient()
        info = plex.get_user(db_id)
        if request.method == "POST":
            plex.update_user(info, request.form)
    else:
        jf = JellyfinClient()
        user_record = User.query.get(db_id)
        jf_id = user_record.token if user_record else None
        info = jf.get_user(jf_id)
        if request.method == "POST":
            info = jf.update_user(jf_id, request.form) or info

    return render_template("admin/user.html", user=info, db_id=db_id)