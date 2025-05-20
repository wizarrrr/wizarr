# app/blueprints/wizard/routes.py
from flask import Blueprint, render_template, request, make_response
from app.extensions import db
from app.models import Settings
from app.services.ombi_client import run_all_importers

wizard_bp = Blueprint("wizard", __name__, url_prefix="/wizard")

# ────────── first page (downloads) ──────────────────────────────────────────
@wizard_bp.route("/", methods=["GET"])
def start():
    run_all_importers()
    # fetch the server_type setting
    server_type = (
        db.session
          .query(Settings.value)
          .filter_by(key="server_type")
          .scalar()
    )
    resp = make_response(render_template(
        "wizard.html",
        server_type=server_type,
    ))
    resp.set_cookie("current", "0")
    return resp

# ────────── previous / next step (AJAX) ─────────────────────────────────────
@wizard_bp.route("/action=<action>", methods=["POST"])
def step(action):
    videos = {
        "en": {"web_video": "...", "app_video": "..."},
        "fr": {"web_video": "...", "app_video": "..."},
    }
    
    # todo: detect via your locale helper
    lang = "en"

    current = int(request.cookies.get("current", 0))

    # load all settings into a dict
    settings = {s.key: s.value for s in Settings.query.all()}
    server_type = settings.get("server_type", "")

    steps = [f"wizard/{server_type}/download.html"]
    if settings.get("overseerr_url"):
        steps.append("wizard/requests.html")
    if settings.get("discord_id"):
        steps.append("wizard/discord.html")
    if settings.get("custom_html"):
        steps.append("wizard/custom.html")
    steps.append(f"wizard/{server_type}/tips.html")

    # decide next index
    if action == "next":
        idx = min(current + 1, len(steps) - 1)
    else:
        idx = max(current - 1, 0)

    resp = make_response(render_template(
        steps[idx],
        videos=videos,
        video_lang=lang,
        # pass through any optional bits
        **{k: settings.get(k) for k in ("discord_id", "overseerr_url", "custom_html")},
        **{action: True},
    ))
    resp.headers["current"] = str(idx)
    resp.headers["max"]     = "1" if idx == len(steps) - 1 else "0"
    resp.set_cookie("current", str(idx))
    return resp
