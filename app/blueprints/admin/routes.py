import datetime
import logging
import os
from urllib.parse import urlparse

from flask import Blueprint, redirect, render_template, request, url_for
from flask_babel import _
from flask_login import login_required

from app.extensions import db
from app.models import (
    Identity,
    Invitation,
    Library,
    MediaServer,
    Settings,
    User,
    invitation_servers,
)
from app.services.invites import create_invite
from app.services.media.service import (
    EMAIL_RE,
    delete_user,
    get_now_playing_all_servers,
    list_users_all_servers,
    list_users_for_server,
    scan_libraries_for_server,
)
from app.services.update_check import check_update_available, get_sponsors

admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/admin")
@login_required
def dashboard():
    __version__ = os.getenv("APP_VERSION", "dev")
    update_available = check_update_available(__version__)
    sponsors = get_sponsors()

    return render_template(
        "admin.html",
        update_available=update_available,
        sponsors=sponsors,
        version=__version__,
    )


# New home dashboard with now playing cards
@admin_bp.route("/home")
@login_required
def home():
    if not request.headers.get("HX-Request"):
        return redirect(url_for(".dashboard"))

    servers = MediaServer.query.order_by(MediaServer.name).all()
    return render_template("admin/home.html", servers=servers)


# HTMX endpoint for now playing cards
@admin_bp.route("/now-playing-cards")
@login_required
def now_playing_cards():
    try:
        sessions = get_now_playing_all_servers()
        return render_template("admin/now_playing_cards.html", sessions=sessions)
    except Exception as e:
        logging.error(f"Failed to get now playing data: {e}")
        return render_template(
            "admin/now_playing_cards.html", sessions=[], error=str(e)
        )


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
    if request.method == "POST":
        chosen_ids = request.form.getlist("server_ids") or (
            [request.form.get("server_id")] if request.form.get("server_id") else []
        )
    else:
        chosen_ids = (
            [request.args.get("server_id")] if request.args.get("server_id") else []
        )

    # pick first selected server to drive contextual UI (plex-specific toggles etc.)
    target_server = None
    for sid in chosen_ids:
        if sid:
            target_server = MediaServer.query.get(int(sid))
            break
    if not target_server:
        target_server = first_server

    server_type = target_server.server_type if target_server else None
    allow_downloads = bool(getattr(target_server, "allow_downloads", False))
    allow_live_tv = bool(getattr(target_server, "allow_live_tv", False))

    if request.method == "POST":
        from app.models import WizardBundle

        bundles = WizardBundle.query.order_by(WizardBundle.name).all()

        try:
            invite = create_invite(request.form)
        except ValueError as e:
            # Return user-friendly error message
            error_message = str(e)
            return render_template(
                "modals/invite.html",
                error_message=error_message,
                server_type=server_type,
                allow_downloads=allow_downloads,
                allow_live_tv=allow_live_tv,
                servers=servers,
                chosen_server_id=target_server.id if target_server else None,
                bundles=bundles,
            ), 400

        current_url = request.headers.get("HX-Current-URL")
        parsed_url = urlparse(current_url)
        host_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        link = f"{host_url}/j/{invite.code}"

        invitations = Invitation.query.order_by(Invitation.created.desc()).all()
        return render_template(
            "modals/invite.html",
            link=link,
            invitations=invitations,
            server_type=server_type,
            allow_downloads=allow_downloads,
            allow_live_tv=allow_live_tv,
            servers=servers,
            chosen_server_id=target_server.id if target_server else None,
            bundles=bundles,
        )

    # GET → initial render
    from app.models import WizardBundle

    bundles = WizardBundle.query.order_by(WizardBundle.name).all()
    return render_template(
        "modals/invite.html",
        server_type=server_type,
        allow_downloads=allow_downloads,
        allow_live_tv=allow_live_tv,
        servers=servers,
        chosen_server_id=target_server.id if target_server else None,
        bundles=bundles,
    )


# standalone /invites page (shell around HTMX)
@admin_bp.route("/invites")
@login_required
def invites():
    if not request.headers.get("HX-Request"):
        return redirect(url_for(".dashboard"))
    servers = MediaServer.query.order_by(MediaServer.name).all()
    return render_template("admin/invites.html", servers=servers)


@admin_bp.route("/invite/table", methods=["POST"])
@login_required
def invite_table():
    """
    HTMX partial that renders the invitation cards grid.

    Accepts:
      - server filter via POST form data (preferred) or querystring (?server=ID)
      - delete action via querystring (?delete=CODE)

    Returns the 'tables/invite_card.html' partial.
    """
    # ------------------------------------------------------------------
    # 1. Handle server filter + optional delete action
    # ------------------------------------------------------------------
    server_filter = request.form.get("server") or request.args.get("server")

    if code := request.args.get("delete"):
        Invitation.query.filter_by(code=code).delete()  # no need to parens
        db.session.commit()

    # ------------------------------------------------------------------
    # 2. Base query (libraries + servers)
    # ------------------------------------------------------------------
    query = Invitation.query.options(
        db.joinedload(Invitation.libraries).joinedload(Library.server),
        db.joinedload(Invitation.servers),
    ).order_by(Invitation.created.desc())

    # NOTE: If an invitation can point to *multiple* servers,
    # Invitation.server_id won’t filter correctly.
    # Instead join through the association table.
    if server_filter:
        try:
            server_id = int(server_filter)
        except ValueError:
            server_id = None
        if server_id:
            # join to association (assuming relationship Invitation.servers)
            query = Invitation.query.options(
                db.joinedload(Invitation.libraries).joinedload(Library.server),
                db.joinedload(Invitation.servers),
            ).order_by(Invitation.created.desc())

            srv = MediaServer.query.get(server_id)
            server_type = srv.server_type if srv else None
        else:
            server_type = None
    else:
        server_type = None

    # fallback: default settings when no filter
    if server_type is None:
        server_type_setting = Settings.query.filter_by(key="server_type").first()
        server_type = server_type_setting.value if server_type_setting else None

    invites = query.all()

    # ------------------------------------------------------------------
    # 3. Build quick lookup: (invite_id, server_id) -> used bool
    # ------------------------------------------------------------------
    raw_flags = db.session.execute(invitation_servers.select()).fetchall()
    flags = {(r.invite_id, r.server_id): bool(r.used) for r in raw_flags}

    # ------------------------------------------------------------------
    # 4. Time context (timezone aware strongly recommended)
    # ------------------------------------------------------------------
    # If you want local Europe/Paris time, set tzinfo; falling back to naive now.
    # from zoneinfo import ZoneInfo
    # now = datetime.datetime.now(tz=ZoneInfo("Europe/Paris"))
    now = datetime.datetime.now()

    # ------------------------------------------------------------------
    # 5. Annotate invitations for the template (view-model enrichment)
    # ------------------------------------------------------------------
    for inv in invites:
        # ---- expiry / expired ----
        if inv.expires:
            if isinstance(inv.expires, str):
                # Try a couple of formats; adjust as needed.
                expires_str = inv.expires  # Store as string for type safety
                for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S"):
                    try:
                        inv.expires = datetime.datetime.strptime(expires_str, fmt)
                        break
                    except ValueError:
                        continue
            # ensure we have a datetime before comparing
            if isinstance(inv.expires, datetime.datetime):
                inv.expired = inv.expires < now
                inv.rel_expiry = _rel_string(inv.expires, now)  # NEW
            else:
                inv.expired = False
                inv.rel_expiry = _("Unknown")
        else:
            inv.expired = False
            inv.rel_expiry = _("Never")

        # ---- group libraries by server ----
        server_libs: dict[str, list[str]] = {}
        for lib in inv.libraries:
            if not lib.server:  # orphan guard
                continue
            server_libs.setdefault(lib.server.name, []).append(lib.name)
        # Sort names inside each group
        for lst in server_libs.values():
            lst.sort()

        inv.display_libraries_by_server = server_libs
        inv.display_libraries = sorted(
            {lib.name for lib in inv.libraries if lib.server}
        )

        # ---- annotate child servers & compute rollups ----
        any_used = False
        all_used = True
        for srv in inv.servers:
            used = flags.get((inv.id, srv.id), False)
            srv.used_flag = used  # keep legacy
            srv.used = used  # NEW: normalised for template
            if used:
                any_used = True
            else:
                all_used = False

            # library list for this server (by *server name* key)
            libs = server_libs.get(srv.name, [])
            srv.library_names = libs  # Use a non-conflicting attribute name
            srv.library_count = len(libs)

            # normalise type attr (template looks at srv.type)
            srv.type = srv.server_type

            # Optional: if you track per-server user redemption, attach here.
            # setattr(srv, "used_by", <User or None>)

        inv.used = any_used
        inv.all_used = all_used

        # ---- top-level status dot ----
        if inv.expired or inv.all_used:
            inv.top_status = "expired"
        else:
            inv.top_status = "ok"

    # ------------------------------------------------------------------
    # 6. Render partial
    # ------------------------------------------------------------------
    return render_template(
        "tables/invite_card.html",
        server_type=server_type,
        invitations=invites,
        rightnow=now,
    )


# ----------------------------------------------------------------------
# Helper: tiny relative time formatting
# ----------------------------------------------------------------------
def _rel_string(target: datetime.datetime, now: datetime.datetime) -> str:
    """Return a short relative expiry string: 'in 3d', 'in 5h', 'Expired', etc."""
    if target <= now:
        return _("Expired")
    delta = target - now
    secs = int(delta.total_seconds())
    mins = secs // 60
    hours = mins // 60
    days = hours // 24

    if days >= 2:
        return _("in %(n)d d", n=days)  # e.g. in 3 d
    if days == 1:
        return _("in 1 d")
    if hours >= 1:
        return _("in %(n)d h", n=hours)  # in 5 h
    if mins >= 1:
        return _("in %(n)d m", n=mins)  # in 45 m
    return _("soon")


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
    if uid := request.args.get("delete"):
        delete_user(int(uid))
    if multi := request.args.get("delete_multi"):
        for uid in multi.split(","):
            if uid.isdigit():
                delete_user(int(uid))

    # 1) ensure data synced from media servers
    try:
        if server_id:
            srv = MediaServer.query.get(int(server_id))
            if srv:
                list_users_for_server(srv)
        else:
            list_users_all_servers()
    except Exception as exc:
        logging.error("sync users failed: %s", exc)

    # 2) build DB query with eager load to keep session bound
    q = User.query.options(db.joinedload(User.server))
    if server_id:
        q = q.filter(User.server_id == int(server_id))
    if query_text:
        like_pattern = f"%{query_text}%"
        q = q.filter(
            db.or_(User.username.ilike(like_pattern), User.email.ilike(like_pattern))
        )

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
        response = render_template(
            "tables/user_card.html", users=_group_users_for_display(users_flat)
        )
        # Add a script to close the modal after swap
        response += """
<script>
  setTimeout(function() {
    var modal = document.getElementById('modal');
    if (modal) modal.classList.add('hidden');
    var modalUser = document.getElementById('modal-user');
    if (modalUser) while (modalUser.firstChild) { modalUser.removeChild(modalUser.firstChild); }
  }, 50);
</script>
"""
        return response

    # ── GET → serve the compact modal ─────────────────────────────
    return render_template("admin/user_modal.html", user=user)


@admin_bp.post("/invite/scan-libraries")
@login_required
def invite_scan_libraries():
    """Scan libraries for one or multiple selected servers and return grouped checkboxes."""

    from app.models import Library, MediaServer

    # Accept either multi-select checkboxes (server_ids) or legacy single server_id
    ids = request.form.getlist("server_ids") or []
    if not ids and request.form.get("server_id"):
        ids = [request.form.get("server_id")]

    if not ids:
        return '<div class="text-red-500">No server selected</div>', 400

    servers = MediaServer.query.filter(MediaServer.id.in_(ids)).all()
    if not servers:
        return '<div class="text-red-500">Invalid server(s)</div>', 400

    server_libs: dict[int, list[Library]] = {}

    for server in servers:
        try:
            raw = scan_libraries_for_server(server)
            items = raw.items() if isinstance(raw, dict) else [(n, n) for n in raw]
        except Exception as exc:
            logging.warning("Library scan failed for %s: %s", server.name, exc)
            items = []

        for fid, name in items:
            lib = Library.query.filter_by(external_id=fid, server_id=server.id).first()
            if lib:
                lib.name = name
            else:
                lib = Library()
                lib.external_id = fid
                lib.name = name
                lib.server_id = server.id
                db.session.add(lib)
        db.session.flush()
        server_libs[server.id] = (
            Library.query.filter_by(server_id=server.id).order_by(Library.name).all()
        )

    db.session.commit()

    return render_template(
        "partials/server_library_picker.html", servers=servers, server_libs=server_libs
    )


@admin_bp.post("/users/link")
@login_required
def link_accounts():
    ids = request.form.getlist("uids")
    if len(ids) < 2:
        return "", 400
    users = User.query.filter(User.id.in_(ids)).all()
    if users[0].identity:
        identity = users[0].identity
    else:
        identity = Identity()
        identity.primary_email = users[0].email
        identity.primary_username = users[0].username
    db.session.add(identity)
    db.session.flush()
    for u in users:
        u.identity = identity
    db.session.commit()
    all_dict = list_users_all_servers()
    users_flat = [u for lst in all_dict.values() for u in lst]
    return render_template(
        "tables/user_card.html", users=_group_users_for_display(users_flat)
    )


@admin_bp.post("/users/unlink")
@login_required
def unlink_account():
    """Unlink one or more selected user accounts from their shared identity.

    The frontend sends all selected checkboxes named "uids". Accept a list to
    allow bulk-unlink just like the link and delete actions.
    """

    ids = request.form.getlist("uids") or []
    # Fallback for legacy single-param payloads
    single = request.form.get("uid")
    if single:
        ids.append(single)

    # Ensure we have at least one uid to process
    ids = [uid for uid in ids if uid and uid.isdigit()]
    if not ids:
        return "", 400

    users = User.query.filter(User.id.in_(ids)).all()
    if not users:
        return "", 400

    # Track identities that might become orphaned
    identities_to_check = {u.identity_id for u in users if u.identity_id}

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
    return render_template(
        "tables/user_card.html", users=_group_users_for_display(users_flat)
    )


@admin_bp.post("/users/bulk-delete")
@login_required
def bulk_delete_users():
    ids = request.form.getlist("uids")
    for uid in ids:
        delete_user(int(uid))
    all_dict = list_users_all_servers()
    users_flat = [u for lst in all_dict.values() for u in lst]
    return render_template(
        "tables/user_card.html", users=_group_users_for_display(users_flat)
    )


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
        expire_dates = [a.expires for a in lst if a.expires]
        expires = min(expire_dates) if expire_dates else None
        code = next(
            (a.code for a in lst if a.code and a.code not in ("None", "empty")), ""
        )
        allow_sync = any(getattr(a, "allowSync", False) for a in lst)

        primary.accounts = lst
        primary.photo = photo or primary.photo
        primary.expires = expires
        primary.code = code
        primary.allowSync = allow_sync
        cards.append(primary)
    return cards


@admin_bp.route("/user/<int:db_id>/details")
@login_required
def user_details_modal(db_id: int):
    """Return a read-only modal with extended information about a user.

    The modal shows:
    • Join date (if available)
    • List of libraries they can access (server-specific)
    • Policy / configuration flags returned by the MediaClient
    """
    import logging

    from app.services.media.service import get_client_for_media_server

    user = User.query.get_or_404(db_id)

    # ── Join / creation date ─────────────────────────────────────────────
    join_date = None
    if user.identity and user.identity.created_at:
        join_date = user.identity.created_at

    # Determine all linked accounts (same identity) or fallback to current
    accounts = list(user.identity.accounts) if user.identity_id else [user]

    accounts_info = []

    for acct in accounts:
        srv = acct.server
        info: dict = {
            "server_type": srv.server_type if srv else "local",
            "server_name": srv.name if srv else "Local",
            "username": acct.username,
            "libraries": None,
            "policies": None,
        }

        if srv:
            try:
                client = get_client_for_media_server(srv)
                if not hasattr(client, "get_user"):
                    raise AttributeError("Client lacks get_user()")

                # Plex helper expects DB row id; others typically use upstream id stored in token.
                user_arg = acct.id if srv.server_type == "plex" else acct.token
                details = client.get_user(user_arg)

                lib_ids: list[str] | None = None

                if srv.server_type == "plex":
                    # Custom API wrapper returns Policy.sections
                    lib_ids = (details.get("Policy", {}) or {}).get("sections") or []

                elif srv.server_type in ("jellyfin", "emby"):
                    pol = details.get("Policy", {}) or {}
                    enable_all = pol.get("EnableAllFolders", False)
                    enabled = pol.get("EnabledFolders", []) or []
                    # access to all – fallback to None to trigger 'all' UI
                    lib_ids = enabled if not enable_all and enabled else None

                elif srv.server_type in ("audiobookshelf", "abs"):
                    all_flag = (details.get("permissions", {}) or {}).get(
                        "accessAllLibraries", False
                    )
                    enabled = details.get("librariesAccessible", []) or []
                    lib_ids = (
                        enabled if not all_flag and enabled else None
                    )  # all libraries

                # Map IDs to names when possible
                if lib_ids is not None:
                    libs_q = (
                        Library.query.filter(
                            Library.external_id.in_(lib_ids),
                            Library.server_id == srv.id,
                        )
                        .order_by(Library.name)
                        .all()
                    )
                    names = [lib.name for lib in libs_q]
                    # Preserve IDs with no matching DB row so user sees something
                    missing = [
                        lid
                        for lid in lib_ids
                        if lid not in {lib.external_id for lib in libs_q}
                    ]
                    info["libraries"] = names + missing
                else:
                    # lib_ids None means full access – pick all enabled libs for server
                    libs_q = (
                        Library.query.filter_by(server_id=srv.id)
                        .order_by(Library.name)
                        .all()
                    )
                    info["libraries"] = [lib.name for lib in libs_q]

                # Store policies / config for optional display
                info["policies"] = (
                    details.get("Configuration")
                    or details.get("Policy")
                    or details.get("permissions")
                )

            except Exception as exc:
                logging.error(
                    "Failed to fetch user details for account %s/%s: %s",
                    acct.id,
                    acct.username,
                    exc,
                )

        accounts_info.append(info)

    return render_template(
        "admin/user_details_modal.html",
        user=user,
        join_date=join_date,
        accounts_info=accounts_info,
    )


# ──────────────────────────────────────────────────────────────────────
# Identity nickname editor


@admin_bp.route("/identity/<int:identity_id>", methods=["GET", "POST"])
@login_required
def edit_identity(identity_id):
    """Create / update a nickname for an Identity row via HTMX modal."""
    from app.models import Identity

    identity = Identity.query.get_or_404(identity_id)

    if request.method == "POST":
        nickname = request.form.get("nickname", "").strip() or None
        identity.nickname = nickname
        db.session.commit()

        # After save, re-render the user cards grid (same as other actions)
        all_dict = list_users_all_servers()
        users_flat = [u for lst in all_dict.values() for u in lst]
        response = render_template(
            "tables/user_card.html", users=_group_users_for_display(users_flat)
        )
        # Add a script to close the modal after swap
        response += """
<script>
  setTimeout(function() {
    var modal = document.getElementById('modal');
    if (modal) modal.classList.add('hidden');
    var modalUser = document.getElementById('modal-user');
    if (modalUser) while (modalUser.firstChild) { modalUser.removeChild(modalUser.firstChild); }
  }, 50);
</script>
"""
        return response

    # GET → return modal form
    return render_template("modals/edit-identity.html", identity=identity)


# HTMX endpoint for latest accepted invitations card
@admin_bp.route("/accepted-invites-card")
@login_required
def accepted_invites_card():
    """Return a small card with the most recent accepted invitations.

    The card is rendered as a standalone fragment suitable for embedding via
    HTMX. We fetch the *n* most recent invitations that have been used (either
    the legacy ``Invitation.used`` flag or per-server usage via the
    ``invitation_servers`` association table).
    """

    # Number of entries to display – keep the card compact
    LIMIT = 6

    # --- build a sub-query that also covers multi-server invites -------------
    # For invites that target multiple servers, the ``Invitation.used`` flag
    # reflects the *primary* invite only.  To catch per-server acceptances we
    # fall back to the association table and treat any row with
    # ``invitation_servers.used = True`` as an acceptance.
    from sqlalchemy import or_, select

    # ``Invitation.used`` covers the common case.  For the association table we
    # gather the *invite_id* values that are marked used.
    # Build a *select()* of invite IDs that were accepted via the
    # ``invitation_servers`` association table.  Using an explicit *select()*
    # avoids SQLAlchemy 2.x warnings about implicit coercion of Subquery
    # objects when used inside ``IN ( ... )`` clauses.
    used_invite_ids = select(invitation_servers.c.invite_id).where(
        invitation_servers.c.used.is_(True)
    )

    query = (
        Invitation.query
        # eager-load the user + primary server to avoid N+1 lookup
        .options(
            db.joinedload(Invitation.used_by),
            db.joinedload(Invitation.server),
            db.joinedload(Invitation.servers),
        )
        .filter(or_(Invitation.used.is_(True), Invitation.id.in_(used_invite_ids)))
        .order_by(Invitation.used_at.desc().nullslast(), Invitation.created.desc())
        .limit(LIMIT)
    )

    invites = query.all()

    return render_template("admin/accepted_invites_card.html", invites=invites)


# HTMX endpoint for server health card
@admin_bp.route("/server-health-card")
@login_required
def server_health_card():
    """Return a card showing health status of all media servers."""
    try:
        from urllib.parse import urlparse

        import requests

        # Look at HX-Current-URL if HTMX, else fall back to url_root
        current_url = request.headers.get("HX-Current-URL", request.url_root)
        parsed = urlparse(current_url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"

        response = requests.get(
            f"{base_url}/settings/servers/statistics/all",
            cookies=request.cookies,
            timeout=10,
        )

        if response.status_code == 200:
            all_stats = response.json()

            server_health = []

            for server_id, stats in all_stats.items():
                # ----------------------
                # Improved offline detection: even if no explicit "error" key
                # an unreachable REST backend returns *empty* server_stats.  We
                # therefore mark the server online only when we have *some*
                # server_stats content in addition to the absence of "error".
                # ----------------------

                server_stats = stats.get("server_stats", {}) or {}
                user_stats = stats.get("user_stats", {}) or {}

                is_online = ("error" not in stats) and bool(server_stats)

                server_info = {
                    "id": server_id,
                    "name": stats.get("server_name", "Unknown"),
                    "type": stats.get("server_type", "unknown"),
                    "online": is_online,
                    "error": stats.get("error", None),
                }

                if is_online:
                    server_info.update(
                        {
                            "version": server_stats.get("version", "Unknown"),
                            "active_sessions": user_stats.get("active_sessions", 0),
                            "transcoding": server_stats.get("transcoding_sessions", 0),
                            "total_users": user_stats.get("total_users", 0),
                        }
                    )

                server_health.append(server_info)

            # Sort by online status and name
            server_health.sort(key=lambda x: (not x["online"], x["name"]))

            return render_template(
                "admin/server_health_card.html", servers=server_health, success=True
            )
        return render_template(
            "admin/server_health_card.html",
            success=False,
            error="Failed to fetch server health",
        )

    except Exception as e:
        return render_template(
            "admin/server_health_card.html", success=False, error=f"Error: {str(e)}"
        )
