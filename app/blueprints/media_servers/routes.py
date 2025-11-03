import base64

from flask import (
    Blueprint,
    flash,
    jsonify,
    make_response,
    redirect,
    render_template,
    render_template_string,
    request,
    url_for,
)
from flask_login import login_required

from app.extensions import db
from app.models import Library, MediaServer
from app.services.media.service import list_users_for_server, scan_libraries_for_server
from app.services.servers import (
    check_audiobookshelf,
    check_drop,
    check_emby,
    check_jellyfin,
    check_kavita,
    check_komga,
    check_navidrome,
    check_plex,
    check_romm,
)

media_servers_bp = Blueprint("media_servers", __name__, url_prefix="/settings/servers")


def _check_connection(data: dict):
    stype = data["server_type"]
    if stype == "plex":
        return check_plex(data["server_url"], data["api_key"])
    if stype == "emby":
        return check_emby(data["server_url"], data["api_key"])
    if stype == "audiobookshelf":
        return check_audiobookshelf(data["server_url"], data["api_key"])
    if stype == "drop":
        return check_drop(data["server_url"], data["api_key"])
    if stype == "romm":
        username = data.get("server_username", "").strip()
        password = data.get("server_password", "").strip()
        if username and password:
            data["api_key"] = base64.b64encode(
                f"{username}:{password}".encode()
            ).decode()
        return check_romm(data["server_url"], data["api_key"])
    if stype == "komga":
        return check_komga(data["server_url"], data["api_key"])
    if stype == "kavita":
        return check_kavita(data["server_url"], data["api_key"])
    if stype == "navidrome":
        return check_navidrome(data["server_url"], data["api_key"])
    return check_jellyfin(data["server_url"], data["api_key"])


@media_servers_bp.route("", methods=["GET"])  # list all
@login_required
def list_servers():
    servers = MediaServer.query.order_by(MediaServer.name).all()
    if request.headers.get("HX-Request"):
        return render_template("settings/servers.html", servers=servers)
    return render_template("settings/servers.html", servers=servers)


@media_servers_bp.route("/create", methods=["GET", "POST"])
@login_required
def create_server():
    if request.method == "POST":
        data = request.form.to_dict()

        # --- RomM: derive API key from credentials ------------------
        if data.get("server_type") == "romm":
            username = data.get("server_username", "").strip()
            password = data.get("server_password", "").strip()
            if username and password:
                data["api_key"] = base64.b64encode(
                    f"{username}:{password}".encode()
                ).decode()

        ok, error_msg = _check_connection(data)
        if not ok:
            # Re-render modal with error
            resp = make_response(
                render_template("modals/create-server.html", error=error_msg)
            )
            resp.headers["HX-Retarget"] = "#create-server-modal"
            return resp
        server = MediaServer()
        server.name = data["server_name"]
        server.server_type = data["server_type"]
        server.url = data["server_url"]
        server.api_key = data.get("api_key")
        server.external_url = data.get("external_url")
        # Universal options (work for all server types)
        server.allow_downloads = bool(data.get("allow_downloads"))
        server.allow_live_tv = bool(data.get("allow_live_tv"))
        server.verified = True
        db.session.add(server)
        db.session.commit()
        # attach chosen libraries
        chosen = request.form.getlist("libraries")
        if chosen:
            for fid in chosen:
                lib = Library.query.filter_by(
                    external_id=fid, server_id=server.id
                ).first()
                if lib:
                    lib.enabled = True
                else:
                    lib = Library()
                    lib.external_id = fid
                    lib.name = fid
                    lib.server_id = server.id
                    lib.enabled = True
                    db.session.add(lib)
            db.session.commit()

        # Automatically sync users from the newly added server
        try:
            list_users_for_server(server)
        except Exception as exc:
            # Log the error but don't fail the server creation
            import logging

            logging.error(f"Failed to sync users for new server {server.name}: {exc}")

        return redirect(url_for("media_servers.list_servers"))
    # GET
    return render_template("modals/create-server.html", error="")


@media_servers_bp.post("/<int:server_id>/scan-libraries")
@login_required
def scan_server_libraries(server_id):
    server = MediaServer.query.get_or_404(server_id)
    try:
        items = scan_libraries_for_server(server)
    except Exception as exc:
        error_message = str(exc) if str(exc) else "Library scan failed"
        flash(f"Library scan failed: {exc}", "error")
        return (
            f"<div class='text-red-500 p-3 border border-red-300 rounded-lg bg-red-50 dark:bg-red-900 dark:border-red-700'><strong>Error:</strong> {error_message}</div>",
            500,
        )

    # items may be dict or list[str]
    pairs = (
        items.items() if isinstance(items, dict) else [(name, name) for name in items]
    )

    # Delete all old libraries for this server and insert fresh ones
    # This avoids conflicts during migration from name-based to ID-based external_id
    Library.query.filter_by(server_id=server.id).delete()
    db.session.flush()

    # Insert fresh libraries with correct external IDs
    for fid, name in pairs:
        lib = Library()
        lib.external_id = fid
        lib.name = name
        lib.server_id = server.id
        lib.enabled = True
        db.session.add(lib)

    db.session.commit()

    # Render checkboxes partial (reuse existing partials)
    all_libs = Library.query.filter_by(server_id=server.id).order_by(Library.name).all()
    return render_template("partials/library_checkboxes.html", libs=all_libs)


@media_servers_bp.route("/<int:server_id>/edit", methods=["GET", "POST"])
@login_required
def edit_server(server_id):
    server = MediaServer.query.get_or_404(server_id)
    if request.method == "POST":
        data = request.form.to_dict()

        if data.get("server_type") == "romm":
            username = data.get("server_username", "").strip()
            password = data.get("server_password", "").strip()
            if username and password:
                data["api_key"] = base64.b64encode(
                    f"{username}:{password}".encode()
                ).decode()

        ok, error_msg = _check_connection(data)
        if not ok:
            resp = make_response(
                render_template(
                    "modals/edit-server.html", server=server, error=error_msg
                )
            )
            resp.headers["HX-Retarget"] = "#create-server-modal"
            return resp
        server.name = data["server_name"]
        server.server_type = data["server_type"]
        server.url = data["server_url"]
        server.api_key = data.get("api_key")
        server.external_url = data.get("external_url")
        # Universal options (work for all server types)
        server.allow_downloads = bool(data.get("allow_downloads"))
        server.allow_live_tv = bool(data.get("allow_live_tv"))
        # update libraries
        chosen = request.form.getlist("libraries")
        if chosen:
            for lib in Library.query.filter_by(server_id=server.id):
                lib.enabled = lib.external_id in chosen
        db.session.commit()
        return redirect(url_for("media_servers.list_servers"))
    # GET → modal
    return render_template("modals/edit-server.html", server=server, error="")


@media_servers_bp.route("/", methods=["DELETE"])
@login_required
def delete_server():
    """Delete a media server and all its dependent records.

    Cascade deletes (via foreign key constraints) will automatically remove:
    - Users (User.server_id)
    - Libraries (Library.server_id)
    - ExpiredUsers (ExpiredUser.server_id)
    - ActivitySessions (ActivitySession.server_id)
    - HistoricalImportJobs (HistoricalImportJob.server_id)

    SET NULL (via foreign key constraints) will preserve:
    - Invitations (Invitation.server_id will be set to NULL)
    """
    server_id = request.args.get("delete", type=int)
    if server_id is not None:
        server = MediaServer.query.get(server_id)
        if server:
            # Database CASCADE constraints handle all dependent records automatically
            db.session.delete(server)
            db.session.commit()
    if request.headers.get("HX-Request"):
        servers = MediaServer.query.order_by(MediaServer.name).all()
        return render_template("settings/servers.html", servers=servers)
    return redirect(url_for("media_servers.list_servers"))


# -------------------------- NEW ENDPOINT ---------------------------
# Quick connectivity check for a given server. Returns {connected: bool, error: str}
# This is used by the settings UI to display real-time connection status on page load.


@media_servers_bp.get("/<int:server_id>/ping")
@login_required
def ping_server(server_id):
    """Return JSON reflecting whether a media server is currently reachable."""
    server = MediaServer.query.get_or_404(server_id)

    ok, error_msg = _check_connection(
        {
            "server_type": server.server_type,
            "server_url": server.url,
            "api_key": server.api_key,
        }
    )

    # If HTMX request, return a badge HTML snippet so it can replace itself.
    if request.headers.get("HX-Request"):
        if ok:
            cls = "bg-green-100 text-green-800 dark:bg-green-700 dark:text-green-100"
            text = "Connected"
        else:
            cls = "bg-red-100 text-red-800 dark:bg-red-700 dark:text-red-100"
            text = "Connection Error"

        return render_template_string(
            '<span class="inline-flex rounded-full px-2 py-0.5 text-xs font-medium '
            + cls
            + '" title="{{ error_msg }}">{{ text }}</span>',
            text=text,
            error_msg=error_msg or "",
        )

    # Non-HTMX fallback (e.g., API call)
    return jsonify({"connected": ok, "error": error_msg if not ok else None})


# -------------------------- STATISTICS ENDPOINTS ---------------------------


@media_servers_bp.get("/<int:server_id>/statistics")
@login_required
def get_server_statistics(server_id):
    """Return comprehensive statistics for a specific media server."""
    server = MediaServer.query.get_or_404(server_id)

    try:
        # Import the service to get the appropriate client
        from app.services.media.service import get_media_client

        client = get_media_client(server.server_type, media_server=server)
        if not client:
            return jsonify(
                {"error": f"No client available for server type: {server.server_type}"}
            ), 400

        stats = client.statistics()
        stats["server_name"] = server.name
        stats["server_type"] = server.server_type
        stats["server_id"] = server.id

        return jsonify(stats)

    except Exception as e:
        return jsonify(
            {
                "error": f"Failed to get statistics: {e!s}",
                "server_name": server.name,
                "server_type": server.server_type,
                "server_id": server.id,
            }
        ), 500


@media_servers_bp.get("/<int:server_id>/health")
@login_required
def get_server_health(server_id):
    """Return lightweight health statistics without triggering user sync."""
    server = MediaServer.query.get_or_404(server_id)

    try:
        # Import the service to get the appropriate client
        from app.services.media.service import get_media_client

        client = get_media_client(server.server_type, media_server=server)
        if not client:
            return jsonify(
                {"error": f"No client available for server type: {server.server_type}"}
            ), 400

        # Use the new lightweight readonly statistics method
        stats = client.get_readonly_statistics()
        stats["server_name"] = server.name
        stats["server_type"] = server.server_type
        stats["server_id"] = server.id

        return jsonify(stats)

    except Exception as e:
        return jsonify(
            {
                "error": f"Failed to get health statistics: {e!s}",
                "server_name": server.name,
                "server_type": server.server_type,
                "server_id": server.id,
                "user_stats": {"total_users": 0, "active_sessions": 0},
                "server_stats": {"version": "Unknown", "transcoding_sessions": 0},
                "library_stats": {},
                "content_stats": {},
            }
        ), 500


@media_servers_bp.get("/statistics/all")
@login_required
def get_all_statistics():
    """Return statistics for all configured media servers."""
    servers = MediaServer.query.all()
    all_stats = {}

    for server in servers:
        # Extract server data before making client calls to avoid session corruption
        server_data = {
            "id": server.id,
            "name": server.name,
            "server_type": server.server_type,
        }

        try:
            from app.services.media.service import get_media_client

            client = get_media_client(server_data["server_type"], media_server=server)
            if client:
                stats = client.statistics()
                stats["server_name"] = server_data["name"]
                stats["server_type"] = server_data["server_type"]
                stats["server_id"] = server_data["id"]
                all_stats[server_data["id"]] = stats
            else:
                all_stats[server_data["id"]] = {
                    "error": f"No client available for server type: {server_data['server_type']}",
                    "server_name": server_data["name"],
                    "server_type": server_data["server_type"],
                    "server_id": server_data["id"],
                }
        except Exception as e:
            all_stats[server_data["id"]] = {
                "error": f"Failed to get statistics: {e!s}",
                "server_name": server_data["name"],
                "server_type": server_data["server_type"],
                "server_id": server_data["id"],
            }

    return jsonify(all_stats)


@media_servers_bp.get("/statistics/<server_type>")
@login_required
def get_statistics_by_type(server_type):
    """Return statistics for all servers of a specific type."""
    servers = MediaServer.query.filter_by(server_type=server_type).all()

    if not servers:
        return jsonify({"error": f"No servers found of type: {server_type}"}), 404

    type_stats = {}

    for server in servers:
        # Extract server data before making client calls to avoid session corruption
        server_data = {
            "id": server.id,
            "name": server.name,
            "server_type": server.server_type,
        }

        try:
            from app.services.media.service import get_media_client

            client = get_media_client(server_data["server_type"], media_server=server)
            if client:
                stats = client.statistics()
                stats["server_name"] = server_data["name"]
                stats["server_type"] = server_data["server_type"]
                stats["server_id"] = server_data["id"]
                type_stats[server_data["id"]] = stats
            else:
                type_stats[server_data["id"]] = {
                    "error": f"No client available for server type: {server_data['server_type']}",
                    "server_name": server_data["name"],
                    "server_type": server_data["server_type"],
                    "server_id": server_data["id"],
                }
        except Exception as e:
            type_stats[server_data["id"]] = {
                "error": f"Failed to get statistics: {e!s}",
                "server_name": server_data["name"],
                "server_type": server_data["server_type"],
                "server_id": server_data["id"],
            }

    return jsonify(type_stats)


@media_servers_bp.get("/health/all")
@login_required
def get_all_health():
    """Return lightweight health statistics for all servers without triggering user sync."""
    servers = MediaServer.query.all()
    all_health = {}

    for server in servers:
        # Extract server data before making client calls to avoid session corruption
        server_data = {
            "id": server.id,
            "name": server.name,
            "server_type": server.server_type,
        }

        try:
            from app.services.media.service import get_media_client

            client = get_media_client(server_data["server_type"], media_server=server)
            if client:
                # Use lightweight readonly statistics instead of full statistics
                stats = client.get_readonly_statistics()
                stats["server_name"] = server_data["name"]
                stats["server_type"] = server_data["server_type"]
                stats["server_id"] = server_data["id"]
                all_health[server_data["id"]] = stats
            else:
                all_health[server_data["id"]] = {
                    "error": f"No client available for server type: {server_data['server_type']}",
                    "server_name": server_data["name"],
                    "server_type": server_data["server_type"],
                    "server_id": server_data["id"],
                    "user_stats": {"total_users": 0, "active_sessions": 0},
                    "server_stats": {"version": "Unknown", "transcoding_sessions": 0},
                    "library_stats": {},
                    "content_stats": {},
                }
        except Exception as e:
            all_health[server_data["id"]] = {
                "error": f"Failed to get health: {e!s}",
                "server_name": server_data["name"],
                "server_type": server_data["server_type"],
                "server_id": server_data["id"],
                "user_stats": {"total_users": 0, "active_sessions": 0},
                "server_stats": {"version": "Unknown", "transcoding_sessions": 0},
                "library_stats": {},
                "content_stats": {},
            }

    return jsonify(all_health)
