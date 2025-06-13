from flask_babel import _
from pathlib import Path
import frontmatter, markdown
from flask import Blueprint, render_template, abort, request, session, redirect
from flask_login import current_user
from app.models import Settings, MediaServer, Invitation
from app.services.ombi_client import run_all_importers


wizard_bp = Blueprint("wizard", __name__, url_prefix="/wizard")
BASE_DIR  = Path(__file__).resolve().parent.parent.parent.parent / "wizard_steps"

# Only allow access right after signup or when logged in
@wizard_bp.before_request
def restrict_wizard():
    if current_user.is_authenticated:
        return
    if not session.get("wizard_access"):
        return redirect("/")


# ─── helpers ────────────────────────────────────────────────────
def _settings() -> dict[str, str | None]:
    data = {s.key: s.value for s in Settings.query.all()}

    # 1️⃣  Override via current invitation (if any)
    inv_code = session.get("wizard_access")
    if inv_code:
        inv = Invitation.query.filter_by(code=inv_code).first()
        if inv and inv.server:
            srv = inv.server
            data["server_type"] = srv.server_type
            # Prefer external_url; fallback to internal url
            data["server_url"] = srv.external_url or srv.url

    # Prefer the explicitly configured external URL if present
    if data.get("external_url"):
        data.setdefault("server_url", data["external_url"])

    # Otherwise, derive from MediaServer row (external_url -> url)
    if "server_url" not in data or not data["server_url"]:
        # Determine server_type preference
        stype = data.get("server_type")
        row = (
            MediaServer.query.filter_by(server_type=stype).first() if stype else MediaServer.query.first()
        )
        if row:
            data["server_url"] = row.external_url or row.url
    return data


def _eligible(post: frontmatter.Post, cfg: dict) -> bool:
    need = post.get("requires", [])
    return all(cfg.get(k) for k in need)


def _steps(server: str, cfg: dict):
    files = sorted((BASE_DIR / server).glob("*.md"))
    return [frontmatter.load(f) for f in files if _eligible(frontmatter.load(f), cfg)]


def _render(post: frontmatter.Post, ctx: dict) -> str:
    from flask import render_template_string
    # Jinja templates inside the markdown files expect a top-level `settings` variable.
    # Build a context copy that exposes the current config dictionary via this key
    # while still passing through all existing entries and utilities (e.g. the _() gettext).
    _vars = ctx.copy()
    _vars.setdefault("settings", ctx)  # avoid overwriting if already provided
    md = render_template_string(post.content, **_vars)
    return markdown.markdown(md, extensions=["fenced_code", "tables", "attr_list"])


def _serve(server: str, idx: int):
    cfg   = _settings()
    steps = _steps(server, cfg)
    if not steps:
        abort(404)

    # read the dir flag HTMX sends ('' | 'prev' | 'next')
    direction = request.values.get("dir", "")

    idx = max(0, min(idx, len(steps) - 1))
    html = _render(steps[idx], cfg | {"_": _})

    return render_template(
        "wizard/frame.html",
        body_html=html,
        idx=idx,
        max_idx=len(steps) - 1,
        server_type=server,
        direction=direction,          # ← NEW
    )



# ─── routes ─────────────────────────────────────────────────────
@wizard_bp.route("/")
def start():
    """Entry point – choose wizard folder based on invitation or global settings."""
    run_all_importers()

    inv_code = session.get("wizard_access")
    server_type = None
    if inv_code:
        inv = Invitation.query.filter_by(code=inv_code).first()
        if inv and inv.server:
            server_type = inv.server.server_type

    if not server_type:
        server_type = _settings().get("server_type", "plex") or "plex"

    return _serve(server_type, 0)


@wizard_bp.route("/<server>/<int:idx>")
def step(server, idx):
    return _serve(server, idx)
