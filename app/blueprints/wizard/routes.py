from flask_babel import _
from pathlib import Path
import frontmatter, markdown
from flask import Blueprint, render_template, abort, request, session, redirect, url_for
from flask_login import current_user
from app.models import Settings, MediaServer, Invitation, WizardStep, WizardBundle, WizardBundleStep
from app.services.ombi_client import run_all_importers


wizard_bp = Blueprint("wizard", __name__, url_prefix="/wizard")
BASE_DIR  = Path(__file__).resolve().parent.parent.parent.parent / "wizard_steps"

# Only allow access right after signup or when logged in
@wizard_bp.before_request
def restrict_wizard():
    # Determine if the Wizard ACL is enabled (default: True)
    acl_row = Settings.query.filter_by(key="wizard_acl_enabled").first()
    acl_enabled = True  # default behaviour – restrict access
    if acl_row and acl_row.value is not None:
        acl_enabled = str(acl_row.value).lower() != "false"

    # Skip further checks if the ACL feature is disabled
    if not acl_enabled:
        return  # Allow everyone

    # Enforce ACL: allow only authenticated users or invited sessions
    if current_user.is_authenticated:
        return
    if not session.get("wizard_access"):
        return redirect("/")


# ─── helpers ────────────────────────────────────────────────────
def _settings() -> dict[str, str | None]:
    # Load all Settings rows **except** legacy server-specific keys. Those have
    # been migrated to the dedicated ``MediaServer`` table and should no longer
    # be sourced from the generic key/value store.
    LEGACY_KEYS: set[str] = {
        "server_type",
        "server_url",
        "external_url",
        "api_key",
        "server_name",
    }

    data: dict[str, str | None] = {
        s.key: s.value for s in Settings.query.all() if s.key not in LEGACY_KEYS
    }

    # ------------------------------------------------------------------
    # Determine the *active* server context in the following order of
    # precedence:
    #   1️⃣  Explicit invitation (wizard_access session key)
    #   2️⃣  First configured MediaServer row (arbitrary default)
    # If neither exists, the Wizard still needs sensible fallbacks so the
    # markdown templates render without errors.
    # ------------------------------------------------------------------

    srv = None

    # 1️⃣  Invitation override
    inv_code = session.get("wizard_access")
    if inv_code:
        inv = Invitation.query.filter_by(code=inv_code).first()
        if inv and inv.server:
            srv = inv.server

    # 2️⃣  Fallback to the first MediaServer row (if any)
    if srv is None:
        srv = MediaServer.query.first()

    # Populate the derived server fields so that existing Jinja templates that
    # reference ``settings.server_*`` continue to work seamlessly.
    if srv is not None:
        data["server_type"] = srv.server_type
        data["server_url"] = srv.external_url or srv.url
        if srv.external_url:
            data["external_url"] = srv.external_url
        if getattr(srv, "name", None):
            data["server_name"] = srv.name

    # If still missing, supply sane defaults to avoid KeyErrors in templates.
    data.setdefault("server_type", "plex")
    data.setdefault("server_url", "")

    return data


def _eligible(post: frontmatter.Post, cfg: dict) -> bool:
    need = post.get("requires", [])
    return all(cfg.get(k) for k in need)


def _steps(server: str, cfg: dict):
    """Return ordered wizard steps for *server* filtered by eligibility.

    Preference order:
        1. Rows from the new *wizard_step* table (if any exist for the given
           server_type).
        2. Legacy markdown files shipped in the repository (fallback).
    """

    # ─── 1) DB-backed steps ────────────────────────────────────────────────
    try:
        db_rows = (
            WizardStep.query
            .filter_by(server_type=server)
            .order_by(WizardStep.position)
            .all()
        )
    except Exception:
        db_rows = []  # table may not exist during migrations/tests

    if db_rows:
        class _RowAdapter:
            """Lightweight shim exposing the subset of frontmatter.Post API
            used by helper functions: `.content` property and `.get()` for
            access to `requires` metadata.
            """

            __slots__ = ("content", "_requires")

            def __init__(self, row: "WizardStep"):
                self.content = row.markdown
                self._requires = row.requires or []

            # frontmatter.Post.get(key, default)
            def get(self, key, default=None):
                if key == "requires":
                    return self._requires
                return default

        steps = [_RowAdapter(r) for r in db_rows if _eligible(_RowAdapter(r), cfg)]
        if steps:
            return steps

    # ─── 2) Fallback to bundled markdown files ─────────────────────────────
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

        # ── 1️⃣ explicit bundle override ───────────────────────────
        if inv and inv.wizard_bundle_id:
            session['wizard_bundle_id'] = inv.wizard_bundle_id
            # drop any server order session var to avoid conflicts
            session.pop('wizard_server_order', None)
            return redirect(url_for('wizard.bundle_view', idx=0))

        # ── 2️⃣ multi-server combo logic ───────────────────────────
        if inv and inv.servers:
            server_order = sorted(inv.servers, key=lambda s: s.server_type)
            if len(server_order) > 1:
                # store ordered list in session and redirect to combo route
                session['wizard_server_order'] = [s.server_type for s in server_order]
                return redirect(url_for('wizard.combo', idx=0))
            else:
                server_type = server_order[0].server_type

    if not server_type:
        first_srv = MediaServer.query.first()
        server_type = first_srv.server_type if first_srv else "plex"

    return _serve(server_type, 0)


@wizard_bp.route("/<server>/<int:idx>")
def step(server, idx):
    return _serve(server, idx)


# ─── combined wizard for multi-server invites ─────────────────────────────

@wizard_bp.route('/combo/<int:idx>')
def combo(idx: int):
    cfg = _settings()
    order = session.get('wizard_server_order') or []
    if not order:
        # fallback to normal wizard
        return redirect(url_for('wizard.start'))

    # concatenate steps preserving order
    steps: list = []
    for stype in order:
        steps.extend(_steps(stype, cfg))

    if not steps:
        abort(404)

    idx = max(0, min(idx, len(steps)-1))
    html = _render(steps[idx], cfg | {"_": _})

    return render_template(
        "wizard/frame.html",
        body_html=html,
        idx=idx,
        max_idx=len(steps)-1,
        server_type='combo',
        direction=request.values.get('dir',''),
    )

# ─── bundle-specific wizard route ──────────────────────────────

@wizard_bp.route('/bundle/<int:idx>')
def bundle_view(idx: int):
    bundle_id = session.get('wizard_bundle_id')
    if not bundle_id:
        return redirect(url_for('wizard.start'))

    bundle = WizardBundle.query.get(bundle_id)
    if not bundle:
        abort(404)

    # ordered steps via association table
    ordered = (
        WizardBundleStep.query
        .filter_by(bundle_id=bundle_id)
        .order_by(WizardBundleStep.position)
        .all()
    )
    steps_raw = [r.step for r in ordered]

    # adapt to frontmatter-like interface
    class _RowAdapter:
        __slots__ = ('content',)
        def __init__(self, row: WizardStep):
            self.content = row.markdown
        def get(self, key, default=None):
            return None

    steps = [_RowAdapter(s) for s in steps_raw]
    if not steps:
        abort(404)

    idx = max(0, min(idx, len(steps)-1))
    html = _render(steps[idx], _settings() | {'_': _})

    return render_template(
        'wizard/frame.html',
        body_html=html,
        idx=idx,
        max_idx=len(steps)-1,
        server_type='bundle',
        direction=request.values.get('dir',''),
    )
