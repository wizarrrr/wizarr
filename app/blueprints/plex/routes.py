from cachetools import TTLCache, cached
from flask import Blueprint, abort, jsonify, request
from flask_login import login_required

from app.services.media.plex import PlexClient

plex_bp = Blueprint("plex", __name__, url_prefix="/plex")


# ─── /plex/scan  (user supplies URL+token) ────────────────────────────────
@plex_bp.route("/scan", methods=["POST"])
@login_required
def scan():
    plex_url = request.args.get("plex_url")
    plex_token = request.args.get("plex_token")
    if not plex_url or not plex_token:
        abort(400)
    try:
        libs = _scan(plex_url, plex_token)
    except Exception:
        abort(400)
    return jsonify(libs)


# ─── /plex/scan-specific  (use saved admin creds) ─────────────────────────
@plex_bp.route("/scan-specific", methods=["POST"])
@login_required
def scan_specific():
    client = PlexClient()
    try:
        libs = client.libraries()
    except Exception:
        abort(400)
    return jsonify(libs)


# optional cache so the first endpoint isn't hit spammy
@cached(cache=TTLCache(maxsize=128, ttl=300))
def _scan(url, token):
    from plexapi.server import PlexServer

    return [lib.title for lib in PlexServer(url, token).library.sections()]
