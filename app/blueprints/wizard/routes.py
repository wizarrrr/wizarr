from flask_babel import _
from pathlib import Path
import frontmatter, markdown
from flask import Blueprint, render_template, abort, request
from app.models import Settings
from app.services.ombi_client import run_all_importers


wizard_bp = Blueprint("wizard", __name__, url_prefix="/wizard")
BASE_DIR  = Path(__file__).resolve().parent.parent.parent.parent / "wizard_steps"


# ─── helpers ────────────────────────────────────────────────────
def _settings() -> dict[str, str | None]:
    return {s.key: s.value for s in Settings.query.all()}


def _eligible(post: frontmatter.Post, cfg: dict) -> bool:
    need = post.get("requires", [])
    return all(cfg.get(k) for k in need)


def _steps(server: str, cfg: dict):
    files = sorted((BASE_DIR / server).glob("*.md"))
    return [frontmatter.load(f) for f in files if _eligible(frontmatter.load(f), cfg)]


def _render(post: frontmatter.Post, ctx: dict) -> str:
    from flask import render_template_string
    md = render_template_string(post.content, **ctx)
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
    run_all_importers()
    server = _settings().get("server_type", "plex") or "plex"
    return _serve(server, 0)


@wizard_bp.route("/<server>/<int:idx>")
def step(server, idx):
    return _serve(server, idx)
