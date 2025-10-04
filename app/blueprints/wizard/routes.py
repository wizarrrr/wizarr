from pathlib import Path

import frontmatter
import markdown
from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    make_response,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_babel import _
from flask_login import current_user

from app.extensions import db
from app.models import (
    Invitation,
    MediaServer,
    Settings,
    WizardBundle,
    WizardBundleStep,
    WizardStep,
)
from app.services.invite_code_manager import InviteCodeManager
from app.services.ombi_client import run_all_importers

wizard_bp = Blueprint("wizard", __name__, url_prefix="/wizard")
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent / "wizard_steps"


# Only allow access right after signup or when logged in
@wizard_bp.before_request
def restrict_wizard():
    """Restrict wizard access to authenticated users or invited sessions.

    Also validates invite codes on each request to prevent session expiration issues.
    Requirement 13.2: Session expiration checks with user-friendly error messages.
    """
    # Determine if the Wizard ACL is enabled (default: True)
    acl_row = Settings.query.filter_by(key="wizard_acl_enabled").first()
    acl_enabled = True  # default behaviour – restrict access
    if acl_row and acl_row.value is not None:
        acl_enabled = str(acl_row.value).lower() != "false"

    # Skip further checks if the ACL feature is disabled
    if not acl_enabled:
        return None  # Allow everyone

    # Enforce ACL: allow only authenticated users or invited sessions
    if current_user.is_authenticated:
        return None

    # Requirement 13.2: Validate invite code on each request for pre-wizard routes
    if request.endpoint and "pre_wizard" in request.endpoint:
        invite_code = InviteCodeManager.get_invite_code()
        if invite_code:
            is_valid, invitation = InviteCodeManager.validate_invite_code(invite_code)
            if not is_valid:
                # Requirement 13.2: User-friendly error message for expired session
                flash(
                    _(
                        "Your invitation has expired or is no longer valid. Please request a new invitation."
                    ),
                    "error",
                )
                InviteCodeManager.clear_invite_data()
                return redirect(url_for("public.index"))

    if not session.get("wizard_access"):
        # Check if this is coming from an invitation process
        # Allow access if they have recently used an invitation
        if (
            session.get("invitation_in_progress")
            or request.referrer
            and "/j/" in request.referrer
        ):
            return None
        return redirect("/")
    return None


# ─── helpers ────────────────────────────────────────────────────
def _get_server_context(server_type: str) -> dict[str, str | None]:
    """Get server-specific context variables for a given server type"""
    # Find the server for this specific server type
    # Priority: 1) From invitation servers, 2) First server of this type

    server = None

    # 1️⃣ Check if we have an invitation with specific servers
    inv_code = session.get("wizard_access")
    if inv_code:
        inv = Invitation.query.filter_by(code=inv_code).first()
        if inv and inv.servers:
            # Find the server of the requested type
            server = next(
                (s for s in inv.servers if s.server_type == server_type), None
            )

    # 2️⃣ Fallback to first server of this type
    if server is None:
        server = MediaServer.query.filter_by(server_type=server_type).first()

    # 3️⃣ Last resort: any server
    if server is None:
        server = MediaServer.query.first()

    context = {}
    if server:
        # Server-specific variables that steps can use
        context["external_url"] = server.external_url or server.url or ""
        context["server_url"] = server.url or ""
        context["server_name"] = getattr(server, "name", "") or ""
        context["server_type"] = server.server_type
    else:
        # Fallback values to prevent template errors
        context["external_url"] = ""
        context["server_url"] = ""
        context["server_name"] = ""
        context["server_type"] = server_type

    return context


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


# Removed _eligible function as part of requires system overhaul


def _steps(server: str, cfg: dict, category: str = "post_invite"):
    """Return ordered wizard steps for *server* and *category* filtered by eligibility.

    Args:
        server: Server type (plex, jellyfin, etc.)
        cfg: Configuration dictionary
        category: Step category ('pre_invite' or 'post_invite'), defaults to 'post_invite'

    Preference order:
        1. Rows from the new *wizard_step* table (if any exist for the given
           server_type and category).
        2. Legacy markdown files shipped in the repository (fallback, post_invite only).

    Returns:
        List of wizard steps (frontmatter.Post or _RowAdapter objects)
    """

    # ─── 1) DB-backed steps ────────────────────────────────────────────────
    try:
        db_rows = (
            WizardStep.query.filter_by(server_type=server, category=category)
            .order_by(WizardStep.position)
            .all()
        )
    except Exception as e:
        # Log database query errors for debugging (Requirement 13.3, 13.5)
        current_app.logger.error(
            f"Database error querying wizard steps for {server}/{category}: {e}",
            exc_info=True,
        )
        db_rows = []  # Fallback to empty list or legacy files

    if db_rows:

        class _RowAdapter:
            """Lightweight shim exposing the subset of frontmatter.Post API
            used by helper functions: `.content` property and `.get()`.
            """

            __slots__ = ("content", "_require")

            def __init__(self, row: "WizardStep"):
                self.content = row.markdown
                # Mirror frontmatter key `require` from DB boolean
                self._require = bool(getattr(row, "require_interaction", False))

            # frontmatter.Post.get(key, default)
            def get(self, key, default=None):
                if key == "require":
                    return self._require
                return default

            def __iter__(self):
                """Make _RowAdapter iterable for compatibility."""
                return iter([self])

        steps = [_RowAdapter(r) for r in db_rows]
        if steps:
            return steps

    # ─── 2) Fallback to bundled markdown files ─────────────────────────────
    # Legacy markdown files are always treated as post_invite only
    if category == "post_invite":
        files = sorted((BASE_DIR / server).glob("*.md"))
        return [frontmatter.load(str(f)) for f in files]

    # No pre_invite steps in legacy files
    return []


def _gather_steps_with_phases(
    server: str,
    cfg: dict,
    *,
    include_pre: bool = False,
    include_post: bool = True,
) -> tuple[list, list[str]]:
    """Collect wizard steps along with their category for downstream rendering."""

    ordered_steps: list = []
    phases: list[str] = []

    if include_pre:
        pre_steps = _steps(server, cfg, category="pre_invite")
        ordered_steps.extend(pre_steps)
        phases.extend(["pre"] * len(pre_steps))

    if include_post:
        post_steps = _steps(server, cfg, category="post_invite")
        ordered_steps.extend(post_steps)
        phases.extend(["post"] * len(post_steps))

    return ordered_steps, phases


def _render(post, ctx: dict, server_type: str | None = None) -> str:
    """Render a post (frontmatter.Post or _RowAdapter) with context.

    Handles rendering errors gracefully by logging and returning error message.
    Requirement 13.6: Graceful degradation for missing/broken steps.
    """
    from app.services.wizard_widgets import (
        process_card_delimiters,
        process_widget_placeholders,
    )

    try:
        # Jinja templates inside the markdown files expect a top-level `settings` variable.
        # Build a context copy that exposes the current config dictionary via this key
        # while still passing through all existing entries and utilities (e.g. the _() gettext).
        render_ctx = ctx.copy()
        render_ctx["settings"] = ctx

        # Add server_type to context if provided and not None
        if server_type is not None:
            render_ctx["server_type"] = server_type

        # FIRST: Process card delimiters (|||) BEFORE widget placeholders
        content_with_cards = process_card_delimiters(post.content)

        # SECOND: Process widget placeholders BEFORE Jinja rendering
        # This prevents Jinja from trying to parse {{ widget:... }} syntax
        content_with_widgets = content_with_cards
        if server_type:
            content_with_widgets = process_widget_placeholders(
                content_with_cards, server_type, context=render_ctx
            )

        # THEN: Render Jinja templates in the processed content
        env = current_app.jinja_env.overlay(autoescape=False)
        template = env.from_string(content_with_widgets)
        rendered_content = template.render(**render_ctx)

        # Use simple markdown configuration - HTML should pass through by default
        return markdown.markdown(
            rendered_content, extensions=["fenced_code", "tables", "attr_list"]
        )
    except Exception as e:
        # Requirement 13.6: Log error and return graceful fallback
        current_app.logger.error(
            f"Error rendering wizard step for {server_type}: {e}", exc_info=True
        )
        # Return a user-friendly error message in HTML
        return f"""
        <div class="alert alert-error">
            <h3>{_("Error Loading Step")}</h3>
            <p>{_("This step could not be loaded. Please contact the administrator or skip to the next step.")}</p>
        </div>
        """


def _serve_wizard(
    server: str,
    idx: int,
    steps: list,
    phase: str,
    *,
    completion_url: str | None = None,
    completion_label: str | None = None,
    current_step_phase: str | None = None,
):
    """Common wizard rendering logic for both pre and post-wizard.

    Args:
        server: Server type (plex, jellyfin, etc.)
        idx: Current step index
        steps: List of wizard steps (frontmatter.Post or _RowAdapter objects)
        phase: 'pre' or 'post' to indicate which phase

    Returns:
        Rendered template response with appropriate headers
    """
    if not steps:
        abort(404)

    cfg = _settings()
    # read the dir flag HTMX sends ('' | 'prev' | 'next')
    direction = request.values.get("dir", "")

    idx = max(0, min(idx, len(steps) - 1))
    post = steps[idx]

    # Merge server-specific context (external_url, server_url, etc.) into config
    server_ctx = _get_server_context(server)
    html = _render(post, cfg | server_ctx | {"_": _}, server_type=server)

    # Determine if this step requires interaction (front matter `require: true` or DB flag)
    require_interaction = False
    try:
        require_interaction = bool(
            getattr(post, "get", lambda k, d=None: None)("require", False)
        )
    except Exception:
        require_interaction = False

    # Determine which template to use based on request type
    if not request.headers.get("HX-Request"):
        # Initial page load - full wrapper with UI chrome
        page = "wizard/frame.html"
    else:
        # HTMX request - content-only partial
        page = "wizard/_content.html"

    # Determine which phase label should be displayed for the current step. Preview
    # flows pass in the actual category per step, while legacy routes rely on the
    # global ``phase`` flag.
    display_phase = None
    if current_step_phase in {"pre", "post"}:
        display_phase = current_step_phase
    elif phase in {"pre", "post"}:
        display_phase = phase

    response = render_template(
        page,
        body_html=html,
        idx=idx,
        max_idx=len(steps) - 1,
        server_type=server,
        direction=direction,
        require_interaction=require_interaction,
        phase=phase,  # NEW: Pass phase to template
        step_phase=display_phase,
        completion_url=completion_url,
        completion_label=completion_label,
    )

    # Add custom headers for client-side updates (HTMX requests only)
    if request.headers.get("HX-Request"):
        from flask import make_response

        resp = make_response(response)
        resp.headers["X-Wizard-Idx"] = str(idx)
        resp.headers["X-Require-Interaction"] = (
            "true" if require_interaction else "false"
        )
        resp.headers["X-Wizard-Step-Phase"] = display_phase or ""
        return resp

    return response


def _serve(server: str, idx: int):
    """Legacy serve function - maintained for backward compatibility.

    This function now delegates to _serve_wizard() with default post_invite phase.
    """
    cfg = _settings()
    steps, _ = _gather_steps_with_phases(server, cfg, include_post=True)
    return _serve_wizard(server, idx, steps, phase="post", current_step_phase="post")


def _get_server_type_from_invitation(invitation: Invitation) -> str | None:
    """Get server type from invitation.

    Args:
        invitation: Invitation object

    Returns:
        Server type string (e.g., 'plex', 'jellyfin') or None if no servers configured

    Note:
        This function maintains server-agnostic architecture by never hardcoding
        a specific server type as a fallback. If no servers are configured,
        it returns None and the caller should handle this appropriately.
    """
    # Priority 1: Check new many-to-many relationship
    if hasattr(invitation, "servers") and invitation.servers:
        return invitation.servers[0].server_type

    # Priority 2: Check legacy single server relationship (backward compatibility)
    if hasattr(invitation, "server") and invitation.server:
        return invitation.server.server_type

    # Priority 3: Fallback to first configured server in the system
    first_srv = MediaServer.query.first()
    if first_srv:
        return first_srv.server_type

    # No servers configured - return None to signal error condition
    return None


# ─── routes ─────────────────────────────────────────────────────
@wizard_bp.route("/pre-wizard")
@wizard_bp.route("/pre-wizard/<int:idx>")
def pre_wizard(idx: int = 0):
    """Display pre-invite wizard steps before user accepts invitation.

    This endpoint shows wizard steps that should be viewed before the user
    accepts an invitation and creates their account. It validates the invite
    code on each request and redirects appropriately if:
    - Invite code is invalid/expired
    - No pre-invite steps exist for the invitation's service
    - No media servers are configured

    For multi-server invitations, this redirects to the combo route with
    category=pre_invite to show steps from all servers in sequence.

    Requirements: 6.1-6.8, 13.1, 13.2, 13.5

    Args:
        idx: Current step index (default: 0)

    Returns:
        Rendered wizard template or redirect response
    """
    # Requirement 13.1: Validate invite code from session
    invite_code = InviteCodeManager.get_invite_code()
    if not invite_code:
        # Requirement 13.1: User-friendly error message for invalid invite code
        flash(_("Invalid or expired invitation"), "error")
        current_app.logger.warning("Pre-wizard accessed without invite code in session")
        return redirect(url_for("public.index"))

    is_valid, invitation = InviteCodeManager.validate_invite_code(invite_code)

    if not is_valid or not invitation:
        # Requirement 13.1, 13.2: User-friendly error for invalid/expired invitation
        flash(_("Invalid or expired invitation"), "error")
        current_app.logger.warning(
            f"Pre-wizard accessed with invalid invite code: {invite_code}"
        )
        InviteCodeManager.clear_invite_data()
        return redirect(url_for("public.index"))

    # Check if this is a multi-server invitation
    # Priority 1: Check new many-to-many relationship
    servers = []
    try:
        if hasattr(invitation, "servers") and invitation.servers:
            # Access the relationship - SQLAlchemy will load it
            servers = list(invitation.servers)  # type: ignore
    except Exception as e:
        # Requirement 13.3: Database query error handling with fallback
        current_app.logger.error(
            f"Error loading servers for invitation {invite_code}: {e}", exc_info=True
        )
        servers = []

    # Priority 2: Check legacy single server relationship
    if not servers and hasattr(invitation, "server") and invitation.server:
        try:
            servers = [invitation.server]
        except Exception as e:
            current_app.logger.error(
                f"Error loading legacy server for invitation {invite_code}: {e}",
                exc_info=True,
            )
            servers = []

    # Handle multi-server invitations (Requirements 10.1, 10.2, 10.3, 10.4)
    if len(servers) > 1:
        # Set up wizard_server_order for combo route
        server_order = [s.server_type for s in servers]
        session["wizard_server_order"] = server_order

        # Redirect to combo route with pre_invite category
        return redirect(url_for("wizard.combo", idx=idx, category="pre_invite"))

    # Single server invitation - handle normally
    # Determine server type from invitation
    server_type = _get_server_type_from_invitation(invitation)

    # Handle case where no servers are configured
    if not server_type:
        # Requirement 13.6: Graceful degradation when no servers configured
        flash(
            _(
                "No media servers are configured. Please contact the administrator to set up a media server."
            ),
            "error",
        )
        current_app.logger.error(f"No servers configured for invitation {invite_code}")
        return redirect(url_for("public.index"))

    # Get pre-invite steps with error handling
    try:
        cfg = _settings()
        steps = _steps(server_type, cfg, category="pre_invite")
    except Exception as e:
        # Requirement 13.3: Database query error handling
        current_app.logger.error(
            f"Error loading pre-wizard steps for {server_type}: {e}", exc_info=True
        )
        # Requirement 13.6: Graceful degradation - redirect to join page
        flash(
            _("Unable to load wizard steps. Proceeding to invitation acceptance."),
            "warning",
        )
        InviteCodeManager.mark_pre_wizard_complete()
        return redirect(url_for("public.invite", code=invite_code))

    if not steps:
        # No pre-invite steps, mark as complete and redirect to join
        InviteCodeManager.mark_pre_wizard_complete()
        return redirect(url_for("public.invite", code=invite_code))

    # Check if user is trying to advance beyond the final step
    direction = request.values.get("dir", "")
    if direction == "next" and (len(steps) == 1 or idx >= len(steps)):
        InviteCodeManager.mark_pre_wizard_complete()
        return redirect(url_for("public.invite", code=invite_code))

    # Render wizard using existing _serve_wizard logic
    return _serve_wizard(
        server_type,
        idx,
        steps,
        "pre",
        completion_url=url_for("wizard.pre_wizard_complete"),
        completion_label=_("Continue to Invite"),
    )


@wizard_bp.route("/pre-wizard/complete")
def pre_wizard_complete():
    """Mark pre-wizard as complete and redirect to the invite page."""

    invite_code = InviteCodeManager.get_invite_code()
    if not invite_code:
        flash(_("Invalid or expired invitation"), "error")
        current_app.logger.warning(
            "Pre-wizard completion attempted without invite code"
        )
        return redirect(url_for("public.index"))

    InviteCodeManager.mark_pre_wizard_complete()
    redirect_url = url_for("public.invite", code=invite_code)

    if request.headers.get("HX-Request"):
        # Return an empty HTMX response that instructs the client to perform a full redirect.
        response = make_response("", 204)
        response.headers["HX-Redirect"] = redirect_url
        return response

    return redirect(redirect_url)


@wizard_bp.route("/post-wizard")
@wizard_bp.route("/post-wizard/<int:idx>")
def post_wizard(idx: int = 0):
    """Display post-invite wizard steps after user accepts invitation.

    This endpoint shows wizard steps that should be viewed after the user
    accepts an invitation and creates their account. It validates authentication
    and redirects appropriately if:
    - User is not authenticated and has no wizard_access session
    - No post-invite steps exist for the service
    - No media servers are configured

    For multi-server invitations, this redirects to the combo route with
    category=post_invite to show steps from all servers in sequence.

    Requirements: 8.1-8.8, 13.2, 13.3, 13.5, 13.6

    Args:
        idx: Current step index (default: 0)

    Returns:
        Rendered wizard template or redirect response
    """
    # Check authentication (user must have accepted invitation)
    # Allow access if user is authenticated OR has wizard_access session
    if not current_user.is_authenticated and not session.get("wizard_access"):
        # Requirement 13.2: User-friendly message for session expiration
        flash(_("Please log in to continue"), "warning")
        current_app.logger.warning("Post-wizard accessed without authentication")
        return redirect(url_for("auth.login"))

    # Determine server type from invitation or first configured server
    server_type = None
    inv_code = session.get("wizard_access")
    invitation = None

    if inv_code:
        try:
            invitation = Invitation.query.filter_by(code=inv_code).first()
        except Exception as e:
            # Requirement 13.3: Database query error handling
            current_app.logger.error(
                f"Error querying invitation {inv_code}: {e}", exc_info=True
            )
            invitation = None

        if invitation:
            # Check if this is a multi-server invitation
            servers = []
            try:
                if hasattr(invitation, "servers") and invitation.servers:
                    servers = list(invitation.servers)  # type: ignore
            except Exception as e:
                # Requirement 13.3: Database query error handling with fallback
                current_app.logger.error(
                    f"Error loading servers for invitation {inv_code}: {e}",
                    exc_info=True,
                )
                servers = []

            # Priority 2: Check legacy single server relationship
            if not servers and hasattr(invitation, "server") and invitation.server:
                try:
                    servers = [invitation.server]
                except Exception as e:
                    current_app.logger.error(
                        f"Error loading legacy server for invitation {inv_code}: {e}",
                        exc_info=True,
                    )
                    servers = []

            # Handle multi-server invitations (Requirements 10.1, 10.2, 10.3, 10.4)
            if len(servers) > 1:
                # Set up wizard_server_order for combo route
                server_order = [s.server_type for s in servers]
                session["wizard_server_order"] = server_order

                # Redirect to combo route with post_invite category
                return redirect(
                    url_for("wizard.combo", idx=idx, category="post_invite")
                )

            # Single server invitation
            server_type = _get_server_type_from_invitation(invitation)

    # Fallback to first configured server if no invitation context
    if not server_type:
        try:
            first_srv = MediaServer.query.first()
            if first_srv:
                server_type = first_srv.server_type
        except Exception as e:
            # Requirement 13.3: Database query error handling
            current_app.logger.error(
                f"Error querying media servers: {e}", exc_info=True
            )

        if not server_type:
            # Requirement 13.6: Graceful degradation when no servers configured
            flash(
                _(
                    "No media servers are configured. Please contact the administrator to set up a media server."
                ),
                "error",
            )
            current_app.logger.error("No media servers configured for post-wizard")
            return redirect(url_for("public.root"))

    # Type guard: At this point, server_type is guaranteed to be a non-empty string
    assert server_type is not None and server_type != ""

    # Check for database-backed post-invite steps specifically
    # We don't want to fall back to legacy markdown files for post-wizard
    try:
        db_steps = (
            WizardStep.query.filter_by(server_type=server_type, category="post_invite")
            .order_by(WizardStep.position)
            .all()
        )
    except Exception as e:
        # Requirement 13.3: Database query error handling
        current_app.logger.error(
            f"Error querying post-wizard steps for {server_type}: {e}", exc_info=True
        )
        db_steps = []

    if not db_steps:
        # No post-invite steps in database, redirect to completion page
        # Requirement 8.2: Redirect to completion page when no post-invite steps exist
        return redirect(url_for("wizard.complete"))

    # Get post-invite steps (will use db_steps or fall back to legacy files)
    try:
        cfg = _settings()
        steps = _steps(server_type, cfg, category="post_invite")
    except Exception as e:
        # Requirement 13.3, 13.6: Database error with graceful degradation
        current_app.logger.error(
            f"Error loading post-wizard steps for {server_type}: {e}", exc_info=True
        )
        # Gracefully complete the wizard
        flash(
            _(
                "Unable to load wizard steps. Setup complete! Welcome to your media server."
            ),
            "success",
        )
        return redirect(url_for("wizard.complete"))

    # Check if user is trying to advance past the final step
    direction = request.values.get("dir", "")
    if direction == "next" and (len(steps) == 1 or idx >= len(steps)):
        # User completed all post-wizard steps
        # Requirement 8.7: Redirect to completion page after completing all steps
        return redirect(url_for("wizard.complete"))

    # Render wizard using existing _serve_wizard logic
    return _serve_wizard(server_type, idx, steps, "post")


@wizard_bp.route("/complete")
def complete():
    """Completion page shown after user finishes all wizard steps.

    This endpoint provides a dedicated completion experience with:
    - Success message confirming setup is complete
    - Clear call-to-action to proceed to the application
    - Automatic cleanup of all invitation-related session data

    Requirements: 8.2, 8.7, 9.4
    """
    # Clear all invitation-related session data
    # Requirement 9.4: Clear all invitation-related data on completion
    InviteCodeManager.clear_invite_data()
    session.pop("wizard_access", None)
    session.pop("wizard_server_order", None)
    session.pop("wizard_bundle_id", None)

    # Show success message
    flash(_("Setup complete! Welcome to your media server."), "success")

    # Redirect to home page (which will redirect to admin dashboard)
    return redirect(url_for("public.root"))


@wizard_bp.route("/")
def start():
    """Entry point – redirect to appropriate wizard based on context.

    This endpoint provides backward compatibility with the old /wizard URL.
    It intelligently redirects users to the appropriate wizard phase:

    - Authenticated users → /post-wizard (they've already accepted an invitation)
    - Users with invite code → /pre-wizard (they're in the invitation flow)
    - Others → home page (no context available)

    Requirements: 8.8, 12.4, 12.5
    """
    run_all_importers()

    # Priority 1: Check if user is authenticated or has wizard_access session
    # These users should see post-wizard steps
    if current_user.is_authenticated or session.get("wizard_access"):
        return redirect(url_for("wizard.post_wizard"))

    # Priority 2: Check for invite code in session (from InviteCodeManager)
    # These users should see pre-wizard steps
    invite_code = InviteCodeManager.get_invite_code()
    if invite_code:
        # Validate the invite code before redirecting
        is_valid, invitation = InviteCodeManager.validate_invite_code(invite_code)
        if is_valid and invitation:
            return redirect(url_for("wizard.pre_wizard"))
        # Invalid invite code - clear it and fall through to home redirect
        InviteCodeManager.clear_invite_data()

    # Priority 3: No context available - redirect to home page
    return redirect(url_for("public.index"))


@wizard_bp.route("/<server>/<int:idx>")
def step(server, idx):
    cfg = _settings()
    steps, phases = _gather_steps_with_phases(
        server,
        cfg,
        include_pre=True,
        include_post=True,
    )

    if not steps:
        abort(404)

    normalized_idx = max(0, min(idx, len(steps) - 1))
    current_phase = phases[normalized_idx] if phases else None

    return _serve_wizard(
        server,
        normalized_idx,
        steps,
        phase="preview",
        current_step_phase=current_phase,
    )


# ─── combined wizard for multi-server invites ─────────────────────────────


@wizard_bp.route("/combo/<int:idx>")
def combo(idx: int):
    """Combined wizard for multi-server invites with category support.

    This route handles multi-server invitations by concatenating wizard steps
    from all servers in the invitation. It supports both pre-invite and post-invite
    categories, determined by the 'category' query parameter.

    Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 13.3, 13.5, 13.6

    Args:
        idx: Current step index

    Query Parameters:
        category: 'pre_invite' or 'post_invite' (default: 'post_invite')

    Returns:
        Rendered wizard template or redirect response
    """
    try:
        cfg = _settings()
    except Exception as e:
        # Requirement 13.3: Database error handling
        current_app.logger.error(
            f"Error loading settings for combo wizard: {e}", exc_info=True
        )
        flash(_("Unable to load wizard configuration. Please try again."), "error")
        return redirect(url_for("wizard.start"))

    order = session.get("wizard_server_order") or []
    if not order:
        # fallback to normal wizard
        current_app.logger.warning(
            "Combo wizard accessed without server order in session"
        )
        return redirect(url_for("wizard.start"))

    # Determine category from query parameter (default: post_invite for backward compatibility)
    category = request.args.get("category", "post_invite")
    if category not in ["pre_invite", "post_invite"]:
        category = "post_invite"

    # Determine phase for template rendering
    phase = "pre" if category == "pre_invite" else "post"
    invite_code = InviteCodeManager.get_invite_code()
    completion_url = url_for("wizard.pre_wizard_complete") if phase == "pre" else None
    completion_label = _("Continue to Invite") if phase == "pre" else None

    # Concatenate steps preserving order AND track which server each step belongs to
    # Requirements 10.1, 10.2: Concatenate pre/post-invite steps for all servers
    steps: list = []
    step_server_mapping: list = []  # Track which server type each step belongs to

    for stype in order:
        # Get steps for this server type with the specified category
        try:
            server_steps = _steps(stype, cfg, category=category)
            steps.extend(server_steps)
            # Requirement 10.3: Maintain server type tracking for each step
            step_server_mapping.extend([stype] * len(server_steps))
        except Exception as e:
            # Requirement 13.3, 13.6: Log error but continue with other servers
            current_app.logger.error(
                f"Error loading steps for {stype}/{category} in combo wizard: {e}",
                exc_info=True,
            )

    # Requirements 10.5, 10.6: Handle case where no steps exist for any server
    if not steps:
        if category == "pre_invite":
            # No pre-invite steps for any server - mark complete and redirect to join
            InviteCodeManager.mark_pre_wizard_complete()
            if invite_code:
                return redirect(url_for("public.invite", code=invite_code))
            return redirect(url_for("wizard.start"))
        # No post-invite steps for any server - redirect to completion
        # Requirement 10.6: Redirect to completion page when no post-invite steps exist
        return redirect(url_for("wizard.complete"))

    # Requirement 10.4: Ensure progress is maintained across server transitions
    idx = max(0, min(idx, len(steps) - 1))

    # Check if we're on the last step and moving forward
    direction = request.values.get("dir", "")
    if direction == "next" and (len(steps) == 1 or idx >= len(steps)):
        if category == "pre_invite":
            # Completed all pre-invite steps for all servers
            InviteCodeManager.mark_pre_wizard_complete()
            if invite_code:
                return redirect(url_for("public.invite", code=invite_code))
            return redirect(url_for("wizard.start"))
        # Completed all post-invite steps for all servers
        # Requirement 8.7: Redirect to completion page after completing all steps
        return redirect(url_for("wizard.complete"))

    # Requirement 10.3: Get the server type for the current step
    current_server_type = (
        step_server_mapping[idx] if idx < len(step_server_mapping) else order[0]
    )

    post = steps[idx]
    # Merge server-specific context for the current step's server
    server_ctx = _get_server_context(current_server_type)
    html = _render(post, cfg | server_ctx | {"_": _}, server_type=current_server_type)

    require_interaction = False
    try:
        require_interaction = bool(
            getattr(post, "get", lambda k, d=None: None)("require", False)
        )
    except Exception:
        require_interaction = False

    # Determine which template to use based on request type
    if not request.headers.get("HX-Request"):
        # Initial page load - full wrapper with UI chrome
        page = "wizard/frame.html"
    else:
        # HTMX request - content-only partial
        page = "wizard/_content.html"

    response = render_template(
        page,
        body_html=html,
        idx=idx,
        max_idx=len(steps) - 1,
        server_type="combo",
        direction=direction,
        require_interaction=require_interaction,
        phase=phase,  # Pass phase based on category
        current_server_type=current_server_type,  # NEW: Pass current server type for display
        completion_url=completion_url,
        completion_label=completion_label,
    )

    # Add custom headers for client-side updates (HTMX requests only)
    if request.headers.get("HX-Request"):
        from flask import make_response

        resp = make_response(response)
        resp.headers["X-Wizard-Idx"] = str(idx)
        resp.headers["X-Require-Interaction"] = (
            "true" if require_interaction else "false"
        )
        resp.headers["X-Current-Server-Type"] = (
            current_server_type  # NEW: Indicate current server
        )
        return resp

    return response


# ─── bundle-specific wizard route ──────────────────────────────


@wizard_bp.route("/bundle/<int:idx>")
def bundle_view(idx: int):
    """Bundle-specific wizard route.

    Note: This function has custom logic for loading steps from bundles,
    so it doesn't use _serve_wizard() directly. However, it maintains the same
    rendering logic and template structure.

    Requirements: 11.1-11.7, 13.3, 13.5, 13.6
    """
    bundle_id = session.get("wizard_bundle_id")
    if not bundle_id:
        current_app.logger.warning(
            "Bundle wizard accessed without bundle_id in session"
        )
        return redirect(url_for("wizard.start"))

    try:
        bundle = db.session.get(WizardBundle, bundle_id)
    except Exception as e:
        # Requirement 13.3: Database query error handling
        current_app.logger.error(
            f"Error loading wizard bundle {bundle_id}: {e}", exc_info=True
        )
        flash(_("Unable to load wizard bundle. Please try again."), "error")
        return redirect(url_for("wizard.start"))

    if not bundle:
        current_app.logger.warning(f"Wizard bundle {bundle_id} not found")
        abort(404)

    # ordered steps via association table
    try:
        ordered = (
            WizardBundleStep.query.filter_by(bundle_id=bundle_id)
            .order_by(WizardBundleStep.position)
            .all()
        )
        steps_raw = [r.step for r in ordered]
    except Exception as e:
        # Requirement 13.3: Database query error handling
        current_app.logger.error(
            f"Error loading steps for bundle {bundle_id}: {e}", exc_info=True
        )
        flash(_("Unable to load wizard steps. Please try again."), "error")
        return redirect(url_for("wizard.start"))

    # adapt to frontmatter-like interface
    class _RowAdapter:
        __slots__ = ("content", "_require")

        def __init__(self, row: WizardStep):
            self.content = row.markdown
            self._require = bool(getattr(row, "require_interaction", False))

        def get(self, key, default=None):
            if key == "require":
                return self._require
            return default

    steps = [_RowAdapter(s) for s in steps_raw]
    if not steps:
        # Requirement 13.6: Graceful degradation for empty bundle
        current_app.logger.warning(f"Wizard bundle {bundle_id} has no steps")
        flash(_("This wizard bundle has no steps configured."), "warning")
        return redirect(url_for("wizard.start"))

    idx = max(0, min(idx, len(steps) - 1))

    # Get the server type and category for the current step from the WizardStep
    current_server_type = steps_raw[idx].server_type if idx < len(steps_raw) else None
    current_category = (
        steps_raw[idx].category if idx < len(steps_raw) else "post_invite"
    )

    # Determine phase based on current step's category
    # Bundles can contain mixed pre/post-invite steps, so we use the current step's category
    phase = "pre" if current_category == "pre_invite" else "post"

    post = steps[idx]

    # Render with error handling
    try:
        settings = _settings()
        html = _render(post, settings | {"_": _}, server_type=current_server_type)
    except Exception as e:
        # Requirement 13.6: Graceful degradation for rendering errors
        current_app.logger.error(
            f"Error rendering bundle step {idx} for bundle {bundle_id}: {e}",
            exc_info=True,
        )
        # Return error message HTML (already handled by _render, but catch any other errors)
        html = f"""
        <div class="alert alert-error">
            <h3>{_("Error Loading Step")}</h3>
            <p>{_("This step could not be loaded. Please contact the administrator or skip to the next step.")}</p>
        </div>
        """

    require_interaction = False
    try:
        require_interaction = bool(
            getattr(post, "get", lambda k, d=None: None)("require", False)
        )
    except Exception:
        require_interaction = False

    # Determine which template to use based on request type
    if not request.headers.get("HX-Request"):
        # Initial page load - full wrapper with UI chrome
        page = "wizard/frame.html"
    else:
        # HTMX request - content-only partial
        page = "wizard/_content.html"

    response = render_template(
        page,
        body_html=html,
        idx=idx,
        max_idx=len(steps) - 1,
        server_type="bundle",
        direction=request.values.get("dir", ""),
        require_interaction=require_interaction,
        phase=phase,  # Phase determined by current step's category
    )

    # Add custom headers for client-side updates (HTMX requests only)
    if request.headers.get("HX-Request"):
        from flask import make_response

        resp = make_response(response)
        resp.headers["X-Wizard-Idx"] = str(idx)
        resp.headers["X-Require-Interaction"] = (
            "true" if require_interaction else "false"
        )
        return resp

    return response
