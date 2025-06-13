import logging
from flask import Blueprint, render_template, request, redirect, abort, url_for
from app.services.invites import create_invite
from app.services.media.service import list_users, delete_user, list_users_all_servers, list_users_for_server, scan_libraries_for_server, EMAIL_RE
from app.services.update_check import check_update_available, get_sponsors
from app.extensions import db, htmx
from app.models import Invitation, Settings, User, MediaServer, Library, Identity
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

    # All servers for dropdown
    servers = MediaServer.query.order_by(MediaServer.name).all()
    first_server = servers[0] if servers else None

    # Determine which server is being targeted (id from form or query)
    target_server_id = request.form.get("server_id") if request.method == "POST" else request.args.get("server_id")
    target_server = None
    if target_server_id:
        target_server = MediaServer.query.get(int(target_server_id))
    if not target_server:
        target_server = first_server

    server_type = target_server.server_type if target_server else None
    allow_downloads_plex = bool(getattr(target_server, "allow_downloads_plex", False))
    allow_tv_plex = bool(getattr(target_server, "allow_tv_plex", False))

    if request.method == "POST":
        try:
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
            servers=servers,
            chosen_server_id=target_server.id if target_server else None,
        )

    # GET → initial render
    return render_template(
        "admin/invite.html",
        server_type=server_type,
        allow_downloads_plex=allow_downloads_plex,
        allow_tv_plex=allow_tv_plex,
        servers=servers,
        chosen_server_id=target_server.id if target_server else None,
    )


# standalone /invites page (shell around HTMX)
@admin_bp.route("/invites")
@login_required
def invites():
    if not request.headers.get("HX-Request"):
        return redirect(url_for(".dashboard"))
    servers = MediaServer.query.order_by(MediaServer.name).all()
    return render_template("admin/invites.html", servers=servers)


# HTMX partial for the table cards
@admin_bp.route("/invite/table", methods=["POST"])
@login_required
def invite_table():
    # HTMX uses POST with hx-include to send the <select name="server"> value
    # so prefer form data, but keep query-string fallback for direct links
    server_filter = request.form.get("server") or request.args.get("server")
    if (code := request.args.get("delete")):
        (
            Invitation.query
            .filter_by(code=code)
            .delete()
        )
        db.session.commit()

    query = Invitation.query.options(db.joinedload(Invitation.libraries)).order_by(Invitation.created.desc())
    if server_filter:
        query = query.filter(Invitation.server_id == int(server_filter))
        srv = MediaServer.query.get(int(server_filter))
        server_type = srv.server_type if srv else None
    else:
        server_type = None  # default

    # fallback: default settings when no filter
    if server_type is None:
        server_type_setting = Settings.query.filter_by(key="server_type").first()
        server_type = server_type_setting.value if server_type_setting else None

    invites = query.all()
    now = datetime.datetime.now()

    # annotate expiry
    for inv in invites:
        if inv.expires:
            if isinstance(inv.expires, str):
                inv.expires = datetime.datetime.strptime(
                    inv.expires, "%Y-%m-%d %H:%M"
                )
            inv.expired = inv.expires < now

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
    servers = MediaServer.query.order_by(MediaServer.name).all()
    return render_template("admin/users.html", servers=servers)


@admin_bp.route("/users/table")
@login_required
def users_table():
    server_id = request.args.get("server")
    order = request.args.get("order", "name_asc")
    query_text = request.args.get("q", "").lower()
    # single or multi delete
    if (uid := request.args.get("delete")):
        delete_user(int(uid))
    if (multi := request.args.get("delete_multi")):
        for uid in multi.split(','):
            if uid.isdigit():
                delete_user(int(uid))

    # 1) ensure data synced from media servers
    try:
        if server_id:
            srv = MediaServer.query.get(int(server_id))
            list_users_for_server(srv)
        else:
            list_users_all_servers()
    except Exception as exc:
        logging.error("sync users failed: %s", exc)

    # 2) build DB query with eager load to keep session bound
    q = (
        User.query
        .options(db.joinedload(User.server))
    )
    if server_id:
        q = q.filter(User.server_id == int(server_id))
    if query_text:
        like_pattern = f"%{query_text}%"
        q = q.filter(db.or_(User.username.ilike(like_pattern), User.email.ilike(like_pattern)))

    # sorting
    if order == "name_desc":
        q = q.order_by(db.func.lower(User.username).desc())
    else:
        q = q.order_by(db.func.lower(User.username))

    users = q.all()

    grouped = _group_users_for_display(users)
    return render_template("tables/user_card.html", users=grouped)


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
        all_dict = list_users_all_servers()
        users_flat = [u for lst in all_dict.values() for u in lst]
        return render_template('tables/user_card.html', users=_group_users_for_display(users_flat))

    # ── GET → serve the compact modal ─────────────────────────────
    return render_template("admin/user_modal.html", user=user)


@admin_bp.post('/invite/scan-libraries')
@login_required
def invite_scan_libraries():
    from app.services.media.service import scan_libraries_for_server
    from app.models import MediaServer, Library
    sid = request.form.get('server_id')
    if not sid:
        return '<div class="text-red-500">No server selected</div>', 400
    server = MediaServer.query.get(int(sid))
    if not server:
        return '<div class="text-red-500">Invalid server</div>', 400
    try:
        raw = scan_libraries_for_server(server)
        items = raw.items() if isinstance(raw, dict) else [(n,n) for n in raw]
    except Exception as exc:
        logging.warning('Library scan failed: %s', exc)
        return '<div class="text-red-500">Scan failed</div>'
    seen=set()
    for fid,name in items:
        seen.add(fid)
        lib = Library.query.filter_by(external_id=fid, server_id=server.id).first()
        if lib:
            lib.name = name
        else:
            db.session.add(Library(external_id=fid,name=name,server_id=server.id))
    db.session.commit()
    libs = Library.query.filter_by(server_id=server.id).order_by(Library.name).all()
    return render_template('partials/library_checkboxes.html', libs=libs)


@admin_bp.post("/users/link")
@login_required
def link_accounts():
    ids = request.form.getlist('uids')
    if len(ids) < 2:
        return '', 400
    users = User.query.filter(User.id.in_(ids)).all()
    identity = users[0].identity or Identity(primary_email=users[0].email, primary_username=users[0].username)
    db.session.add(identity)
    db.session.flush()
    for u in users:
        u.identity = identity
    db.session.commit()
    all_dict = list_users_all_servers()
    users_flat = [u for lst in all_dict.values() for u in lst]
    return render_template('tables/user_card.html', users=_group_users_for_display(users_flat))

@admin_bp.post('/users/unlink')
@login_required
def unlink_account():
    """Unlink one or more selected user accounts from their shared identity.

    The frontend sends all selected checkboxes named "uids". Accept a list to
    allow bulk-unlink just like the link and delete actions.
    """

    ids = request.form.getlist('uids') or []
    # Fallback for legacy single-param payloads
    single = request.form.get('uid')
    if single:
        ids.append(single)

    # Ensure we have at least one uid to process
    ids = [uid for uid in ids if uid and uid.isdigit()]
    if not ids:
        return '', 400

    users = User.query.filter(User.id.in_(ids)).all()
    if not users:
        return '', 400

    # Track identities that might become orphaned
    identities_to_check = set(u.identity_id for u in users if u.identity_id)

    for user in users:
        user.identity = None

    db.session.commit()

    # Clean up orphaned Identity rows
    from app.models import Identity  # local import to avoid circular refs
    for iid in identities_to_check:
        identity = Identity.query.get(iid)
        if identity and not identity.accounts:
            db.session.delete(identity)
    db.session.commit()

    # Return refreshed grid
    all_dict = list_users_all_servers()
    users_flat = [u for lst in all_dict.values() for u in lst]
    return render_template('tables/user_card.html', users=_group_users_for_display(users_flat))

@admin_bp.post('/users/bulk-delete')
@login_required
def bulk_delete_users():
    ids = request.form.getlist('uids')
    for uid in ids:
        delete_user(int(uid))
    all_dict = list_users_all_servers()
    users_flat = [u for lst in all_dict.values() for u in lst]
    return render_template('tables/user_card.html', users=_group_users_for_display(users_flat))

# Helper: group and enrich users for display
def _group_users_for_display(user_list):
    """Collapse multiple User rows into primary cards.

    • Accounts that share the same `identity_id` are always grouped.
    • If no identity link exists, we *only* group by e-mail when the address
      looks like a real one according to the same regex used by the automatic
      linker.  This prevents users imported from Plex/ABS that have blank or
      placeholder addresses ("None", "", etc.) from being merged together.
    """

    groups: dict[str, list] = {}
    for u in user_list:
        if u.identity_id:
            key = f"id:{u.identity_id}"
        else:
            email = (u.email or "").strip()
            if EMAIL_RE.fullmatch(email):
                key = f"email:{email.lower()}"
            else:
                # Fallback to the user record itself → no unintended merging
                key = f"user:{u.id}"
        groups.setdefault(key, []).append(u)

    cards = []
    for lst in groups.values():
        primary = min(lst, key=lambda x: (x.username or ""))
        photo = next((a.photo for a in lst if a.photo), None)
        expires = min([a.expires for a in lst if a.expires] or [None])
        code = next((a.code for a in lst if a.code and a.code not in ("None","empty")), "")
        allow_sync = any(getattr(a, "allowSync", False) for a in lst)

        primary.accounts = lst
        primary.photo = photo or primary.photo
        primary.expires = expires
        primary.code = code
        primary.allowSync = allow_sync
        cards.append(primary)
    return cards
