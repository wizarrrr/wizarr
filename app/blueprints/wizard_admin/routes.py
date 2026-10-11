from __future__ import annotations

import json
import re
import tempfile
from datetime import UTC, datetime
from typing import cast

import structlog
from flask import (
    Blueprint,
    abort,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)
from flask_babel import gettext as _
from flask_login import login_required
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.forms.wizard import (
    SimpleWizardStepForm,
    WizardBundleForm,
    WizardImportForm,
    WizardPresetForm,
    WizardStepForm,
)
from app.models import MediaServer, WizardBundle, WizardBundleStep, WizardStep
from app.services.wizard_export_import import WizardExportImportService
from app.services.wizard_presets import (
    create_step_from_preset,
    get_available_presets,
    get_preset_title,
)

wizard_admin_bp = Blueprint(
    "wizard_admin",
    __name__,
    url_prefix="/settings/wizard",
)

logger = structlog.get_logger("wizarr.wizard_admin")

# Matches {{ _( "Some text" ) }} or {{ _( 'Some text' ) }} with arbitrary
# whitespace.
_I18N_PATTERN = re.compile(r"{{\s*_\(\s*(['\"])(.*?)\1\s*\)\s*}}", re.DOTALL)


def _strip_localization(md: str) -> str:
    """Remove Jinja gettext wrappers from markdown, leaving plain text."""

    def _replace(match: re.Match) -> str:
        text = match.group(2)
        # Undo lightweight escaping used inside the source markdown
        return text.replace("\\'", "'").replace('"', '"')

    return _I18N_PATTERN.sub(_replace, md)


def _commit_or_rollback() -> bool:
    """Commit the session. Return False if a database constraint stops it.

    On failure, roll back the session so that the rest of the request can
    use the database, and flash an error for the admin.
    """
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        logger.warning("wizard_admin_commit_failed", exc_info=True)
        flash(
            _(
                "Cannot save the change because it conflicts with other wizard "
                "data. Refresh the page and try again."
            ),
            "error",
        )
        return False
    return True


def _commit_reorder():
    """Commit a reorder and return the JSON response for the client."""
    if not _commit_or_rollback():
        return jsonify({"status": "error"}), 409
    return jsonify({"status": "ok"})


def _next_free_position(server_type: str, category: str) -> int:
    """Return the position after the last step of a server type and category."""
    # Do not flush pending changes: they can hold a position that is not free yet.
    with db.session.no_autoflush:
        max_pos = (
            db.session.query(func.max(WizardStep.position))
            .filter_by(server_type=server_type, category=category)
            .scalar()
        )
    return 0 if max_pos is None else max_pos + 1


def _move_step(step: WizardStep, server_type: str, category: str) -> None:
    """Set the server type and category of a step.

    If the group changes, the old position can belong to a step of the new
    group. Thus the step goes to the end of the new group.
    """
    if (server_type, category) != (step.server_type, step.category):
        step.position = _next_free_position(server_type, category)
    step.server_type = server_type
    step.category = category


def _steps_in_order(ids: list[int]) -> list[WizardStep]:
    """Load the steps with these IDs in this order. Skip duplicate and unknown IDs."""
    ids = list(dict.fromkeys(ids))
    by_id = {s.id: s for s in WizardStep.query.filter(WizardStep.id.in_(ids))}
    return [by_id[i] for i in ids if i in by_id]


def _renumber_steps(server_type: str, category: str, steps: list[WizardStep]) -> None:
    """Put the steps into one group in this order, with positions 0 to n-1.

    Steps of the group that are not in the list go to the end. Thus two steps
    never get the same position, also when the client sends an old list.
    """
    rest = (
        WizardStep.query.filter(
            WizardStep.server_type == server_type,
            WizardStep.category == category,
            WizardStep.id.notin_([s.id for s in steps]),
        )
        .order_by(WizardStep.position)
        .all()
    )
    steps = steps + rest

    # Phase 1: temporary negative positions. They do not collide with the
    # current positions or with the final positions.
    for tmp_pos, step in enumerate(steps, start=1):
        step.server_type = server_type
        step.category = category
        step.position = -tmp_pos
    db.session.flush()

    # Phase 2: final 0-based positions.
    for final_pos, step in enumerate(steps):
        step.position = final_pos


@wizard_admin_bp.route("/", methods=["GET"])
@login_required
def list_steps():
    # Group steps by server_type and category for side-by-side display
    rows = (
        # Exclude custom steps (managed via Wizard Bundles) from the default view
        WizardStep.query.filter(WizardStep.server_type != "custom")
        .order_by(WizardStep.server_type, WizardStep.category, WizardStep.position)
        .all()
    )

    # Create nested structure: {server_type: {category: [steps]}}
    grouped: dict[str, dict[str, list[WizardStep]]] = {}
    for row in rows:
        if row.server_type not in grouped:
            grouped[row.server_type] = {"pre_invite": [], "post_invite": []}
        grouped[row.server_type][row.category].append(row)

    # Filter: show only servers that are currently configured/enabled
    active_types = {srv.server_type for srv in MediaServer.query.all()}
    grouped = {
        stype: categories
        for stype, categories in grouped.items()
        if stype in active_types
    }

    # When requested via HTMX we return only the inner fragment that is meant
    # to be swapped into the <div id="tab-body"> container on the settings
    # page.  For a normal full-page navigation we extend the base layout so
    # the <head> section is populated and styling/scripts remain intact.
    tmpl = (
        "settings/wizard/steps.html"
        if request.headers.get("HX-Request")
        else "settings/page.html"  # fallback renders full settings page
    )

    # For the full page fallback we have to render the *entire* settings page
    # with the wizard tab pre-selected.  Rather than duplicating that layout
    # we reuse the existing generic settings page helper and pass a query
    # parameter that the template looks for to auto-open the correct tab.
    if tmpl == "settings/page.html":
        return redirect(url_for("settings.page") + "#wizard")

    return render_template(tmpl, grouped=grouped)


# ─── Bundles view ─────────────────────────────────────────────────────


@wizard_admin_bp.route("/bundles", methods=["GET"])
@login_required
def list_bundles():
    # Clean up orphaned bundle steps before displaying
    orphaned_steps = (
        db.session.query(WizardBundleStep)
        .outerjoin(WizardStep, WizardBundleStep.step_id == WizardStep.id)
        .filter(WizardStep.id.is_(None))
        .all()
    )

    if orphaned_steps:
        for orphaned in orphaned_steps:
            db.session.delete(orphaned)
        if _commit_or_rollback():
            flash(
                _("Cleaned up {} orphaned step(s)").format(len(orphaned_steps)), "info"
            )

    bundles = WizardBundle.query.order_by(WizardBundle.id).all()

    tmpl = (
        "settings/wizard/bundles.html"
        if request.headers.get("HX-Request")
        else "settings/page.html"
    )

    if tmpl == "settings/page.html":
        return redirect(url_for("settings.page") + "#wizard")

    return render_template(tmpl, bundles=bundles)


@wizard_admin_bp.route("/create", methods=["GET", "POST"])
@login_required
def create_step():
    bundle_id = request.args.get("bundle_id", type=int)
    simple = request.args.get("simple") == "1" or bundle_id is not None

    FormCls = SimpleWizardStepForm if simple else WizardStepForm
    form = FormCls(request.form if request.method == "POST" else None)

    if form.validate_on_submit():
        # When using the simple form we slot the step into a synthetic 'custom'
        # server_type so ordering is still unique and existing wizard logic is
        # unaffected.
        server_type_attr = getattr(form, "server_type", None)
        stype = "custom" if simple else (server_type_attr and server_type_attr.data)

        # Get category from form (defaults to 'post_invite')
        category = form.category.data if hasattr(form, "category") else "post_invite"

        max_pos = (
            db.session.query(func.max(WizardStep.position))
            .filter_by(server_type=stype, category=category)
            .scalar()
        )
        next_pos = (max_pos or 0) + 1

        cleaned_md = _strip_localization(form.markdown.data or "")

        step = WizardStep(
            server_type=stype,
            category=category,
            position=next_pos,
            title=(getattr(form, "title", None) and form.title.data) or None,
            markdown=cleaned_md,
            require_interaction=(
                getattr(form, "require_interaction", None) is not None
                and bool(form.require_interaction.data)
            ),
        )
        db.session.add(step)
        db.session.flush()  # get step.id

        # If created from a bundle context attach immediately
        if bundle_id:
            max_bpos = (
                db.session.query(func.max(WizardBundleStep.position))
                .filter_by(bundle_id=bundle_id)
                .scalar()
            )
            next_bpos = (max_bpos or 0) + 1
            db.session.add(
                WizardBundleStep(
                    bundle_id=bundle_id, step_id=step.id, position=next_bpos
                )
            )

        if _commit_or_rollback():
            flash(_("Step created"), "success")

        # HTMX target refresh depending on origin
        if request.headers.get("HX-Request"):
            return list_bundles() if bundle_id else list_steps()

        return redirect(
            url_for(
                "wizard_admin.list_bundles" if bundle_id else "wizard_admin.list_steps"
            )
        )

    # GET – choose modal / full template based on form type
    if simple:
        modal_tmpl = "modals/wizard-simple-step-form.html"
        page_tmpl = "settings/wizard/simple_form.html"
    else:
        modal_tmpl = "modals/wizard-step-form.html"
        page_tmpl = "settings/wizard/form.html"

    tmpl = modal_tmpl if request.headers.get("HX-Request") else page_tmpl
    return render_template(tmpl, form=form, action="create", bundle_id=bundle_id)


@wizard_admin_bp.route("/create-preset", methods=["GET", "POST"])
@login_required
def create_preset():
    """Create wizard step from preset template."""
    form = WizardPresetForm(request.form if request.method == "POST" else None)

    # Populate preset choices
    presets = get_available_presets()
    form.preset_id.choices = [(p.id, p.name) for p in presets]

    if form.validate_on_submit():
        preset_id = form.preset_id.data
        server_type = form.server_type.data

        # Type check: these should not be None after validation
        if not preset_id or not server_type:
            flash("Preset ID and server type are required", "danger")
            return redirect(url_for("wizard_admin.create_preset"))

        # Get category from form (defaults to 'post_invite')
        category = form.category.data or "post_invite"

        # Prepare template variables
        template_vars = {}
        if form.discord_id.data:
            template_vars["discord_id"] = form.discord_id.data
        if form.overseerr_url.data:
            template_vars["overseerr_url"] = form.overseerr_url.data

        try:
            # Create step content from preset
            markdown_content = create_step_from_preset(preset_id, **template_vars)
            title = get_preset_title(preset_id)

            # Find next position for this server type and category
            max_pos = (
                db.session.query(func.max(WizardStep.position))
                .filter_by(server_type=server_type, category=category)
                .scalar()
            )
            next_pos = (max_pos or 0) + 1

            # Create the step
            step = WizardStep(
                server_type=server_type,
                category=category,
                position=next_pos,
                title=title,
                markdown=markdown_content,
            )
            db.session.add(step)
            if _commit_or_rollback():
                flash(_("Preset step created successfully"), "success")

            # HTMX refresh
            if request.headers.get("HX-Request"):
                return list_steps()
            return redirect(url_for("wizard_admin.list_steps"))

        except KeyError as e:
            flash(_("Error creating preset: {}").format(str(e)), "error")

    modal_tmpl = "modals/wizard-preset-form.html"
    page_tmpl = "settings/wizard/preset_form.html"
    tmpl = modal_tmpl if request.headers.get("HX-Request") else page_tmpl

    return render_template(tmpl, form=form, presets=presets, action="create")


@wizard_admin_bp.route("/<int:step_id>/edit", methods=["GET", "POST"])
@login_required
def edit_step(step_id: int):
    step = db.get_or_404(WizardStep, step_id)

    simple = step.server_type == "custom"
    FormCls = SimpleWizardStepForm if simple else WizardStepForm
    form = FormCls(request.form if request.method == "POST" else None, obj=step)

    if form.validate_on_submit():
        server_type = step.server_type
        if not simple:
            server_type_attr = getattr(form, "server_type", None)
            server_type = server_type_attr.data if server_type_attr else "custom"

        # Update category if present on form
        category = step.category
        if hasattr(form, "category") and form.category.data:
            category = form.category.data

        _move_step(step, server_type, category)
        step.title = (getattr(form, "title", None) and form.title.data) or None
        cleaned_md = _strip_localization(form.markdown.data or "")
        step.markdown = cleaned_md

        # Update interaction requirement if present on this form
        if getattr(form, "require_interaction", None) is not None:
            step.require_interaction = bool(form.require_interaction.data)

        if _commit_or_rollback():
            flash(_("Step updated"), "success")

        # HTMX refresh
        if request.headers.get("HX-Request"):
            return list_bundles() if simple else list_steps()

        return redirect(
            url_for(
                "wizard_admin.list_bundles" if simple else "wizard_admin.list_steps"
            )
        )

    # GET: populate fields
    if request.method == "GET":
        form.markdown.data = _strip_localization(step.markdown)

    modal_tmpl = (
        "modals/wizard-simple-step-form.html"
        if simple
        else "modals/wizard-step-form.html"
    )
    page_tmpl = (
        "settings/wizard/simple_form.html" if simple else "settings/wizard/form.html"
    )
    tmpl = modal_tmpl if request.headers.get("HX-Request") else page_tmpl
    return render_template(tmpl, form=form, action="edit", step=step)


@wizard_admin_bp.route("/<int:step_id>/delete", methods=["POST"])
@login_required
def delete_step(step_id: int):
    step = db.get_or_404(WizardStep, step_id)

    # Check if this is a custom step (from bundle context)
    is_custom_step = step.server_type == "custom"

    db.session.delete(step)
    if _commit_or_rollback():
        flash(_("Step deleted"), "success")

    # For HTMX requests return the updated steps list fragment so the client
    # can refresh the table without a full page reload. Otherwise fall back
    # to a normal redirect which lands on the full settings page (wizard tab
    # pre-selected) to keep the UI consistent and fully styled.
    if request.headers.get("HX-Request"):
        return list_bundles() if is_custom_step else list_steps()

    return redirect(url_for("settings.page") + "#wizard")


@wizard_admin_bp.route("/reorder", methods=["POST"])
@login_required
def reorder_steps():
    """Accept JSON with server_type, category, and step IDs in new order.

    Supports two formats:
    1. Legacy format: JSON array of step IDs (for bundle steps)
    2. New format: JSON object with server_type, category, and order array
    """
    data = request.json

    # Handle legacy format (array of IDs)
    if isinstance(data, list):
        steps = _steps_in_order(cast(list[int], data))
        # Each step stays in its group. Renumber each group separately.
        for group in dict.fromkeys((s.server_type, s.category) for s in steps):
            members = [s for s in steps if (s.server_type, s.category) == group]
            _renumber_steps(group[0], group[1], members)
        return _commit_reorder()

    # Handle new format (object with server_type, category, order)
    if not isinstance(data, dict):
        abort(400)

    # Type narrowing: after isinstance check, data is dict[str, Any]
    data_dict = cast(dict[str, object], data)
    server_type = data_dict.get("server_type")
    category = data_dict.get("category")
    order = data_dict.get("order", [])

    if not server_type or not category or not isinstance(order, list):
        abort(400)

    # Type narrowing: after isinstance check, order is a list
    order_list = cast(list[int], order)

    # Validate category
    if category not in ["pre_invite", "post_invite"]:
        abort(400)

    # The listed steps move into this group (drag and drop between categories).
    _renumber_steps(
        cast(str, server_type), cast(str, category), _steps_in_order(order_list)
    )
    return _commit_reorder()


@wizard_admin_bp.route("/preview", methods=["POST"])
@login_required
def preview_markdown():
    from markdown import markdown as md_to_html

    raw = request.form.get("markdown", "")
    return md_to_html(raw, extensions=["fenced_code", "tables", "attr_list"])


# ─── bundle CRUD ─────────────────────────────────────────────────
@wizard_admin_bp.route("/bundle/create", methods=["GET", "POST"])
@login_required
def create_bundle():
    form = WizardBundleForm(request.form if request.method == "POST" else None)

    if form.validate_on_submit():
        bundle = WizardBundle(
            name=form.name.data, description=form.description.data or None
        )
        db.session.add(bundle)
        if _commit_or_rollback():
            flash(_("Bundle created"), "success")

        # For HTMX requests return the updated bundles list fragment so the client
        # can refresh the table without a full page reload. Otherwise fall back
        # to a normal redirect.
        if request.headers.get("HX-Request"):
            return list_bundles()

        return redirect(url_for("wizard_admin.list_bundles"))

    tmpl = (
        "modals/wizard-bundle-form.html"
        if request.headers.get("HX-Request")
        else "settings/wizard/bundle_form.html"
    )
    return render_template(tmpl, form=form, action="create")


@wizard_admin_bp.route("/bundle/<int:bundle_id>/edit", methods=["GET", "POST"])
@login_required
def edit_bundle(bundle_id: int):
    bundle = db.get_or_404(WizardBundle, bundle_id)
    form = WizardBundleForm(
        request.form if request.method == "POST" else None, obj=bundle
    )

    if form.validate_on_submit():
        bundle.name = form.name.data
        bundle.description = form.description.data or None
        if _commit_or_rollback():
            flash(_("Bundle updated"), "success")

        # For HTMX requests return the updated bundles list fragment so the client
        # can refresh the table without a full page reload. Otherwise fall back
        # to a normal redirect.
        if request.headers.get("HX-Request"):
            return list_bundles()

        return redirect(url_for("wizard_admin.list_bundles"))

    tmpl = (
        "modals/wizard-bundle-form.html"
        if request.headers.get("HX-Request")
        else "settings/wizard/bundle_form.html"
    )
    return render_template(tmpl, form=form, action="edit", bundle=bundle)


@wizard_admin_bp.route("/bundle/<int:bundle_id>/delete", methods=["POST"])
@login_required
def delete_bundle(bundle_id: int):
    bundle = db.get_or_404(WizardBundle, bundle_id)
    db.session.delete(bundle)
    if _commit_or_rollback():
        flash(_("Bundle deleted"), "success")

    if request.headers.get("HX-Request"):
        return list_bundles()
    return redirect(url_for("wizard_admin.list_bundles"))


@wizard_admin_bp.route("/bundle/<int:bundle_id>/reorder", methods=["POST"])
@login_required
def reorder_bundle(bundle_id: int):
    payload = request.json  # accepts list of IDs or dict with detailed order
    category_map: dict[int, str | None] = {}

    if isinstance(payload, list):
        order = []
        for entry in payload:
            try:
                order.append(int(entry))
            except (TypeError, ValueError):
                continue
    elif isinstance(payload, dict):
        order_raw = payload.get("order")
        if not isinstance(order_raw, list):
            abort(400)

        order = []
        for entry in order_raw:
            if isinstance(entry, dict):
                step_id = entry.get("id")
                if step_id is None:
                    continue
                try:
                    step_id_int = int(step_id)
                except (TypeError, ValueError):
                    continue
                order.append(step_id_int)
                category_value = entry.get("category")
                # Normalise falsy to None to indicate no change
                if category_value in (None, ""):
                    category_map[step_id_int] = None
                else:
                    category_map[step_id_int] = str(category_value)
            else:
                try:
                    order.append(int(entry))
                except (TypeError, ValueError):
                    continue
    else:
        abort(400)

    rows = (
        WizardBundleStep.query.filter_by(bundle_id=bundle_id)
        .order_by(WizardBundleStep.position)
        .all()
    )
    id_to_row = {r.step_id: r for r in rows}
    listed = [
        id_to_row[step_id] for step_id in dict.fromkeys(order) if step_id in id_to_row
    ]
    # Rows that the request does not list go to the end. Thus two rows never
    # get the same position, also when the client sends an old list.
    rows = listed + [r for r in rows if r not in listed]

    # Phase 1 – temporary negative positions to satisfy unique constraint
    for tmp_pos, row in enumerate(rows, start=1):
        row.position = -tmp_pos

    db.session.flush()

    # Update categories for custom steps when requested
    moved_steps: list[tuple[WizardStep, str]] = []
    for step_id, desired_category in category_map.items():
        if desired_category is None:
            continue
        row = id_to_row.get(step_id)
        if row is None or row.step is None:
            continue
        step = row.step
        if step.category == desired_category:
            continue
        moved_steps.append((step, desired_category))

    if moved_steps:
        next_positions: dict[tuple[str, str], int] = {}

        def get_next_position(server_type: str, category: str) -> int:
            key = (server_type, category)
            if key not in next_positions:
                next_positions[key] = _next_free_position(server_type, category)
            else:
                next_positions[key] += 1
            return next_positions[key]

        with db.session.no_autoflush:
            for step, desired_category in moved_steps:
                step.category = desired_category
                step.position = get_next_position(step.server_type, desired_category)

    # Phase 2 – final 0-based positions
    for final_pos, row in enumerate(rows):
        row.position = final_pos

    return _commit_reorder()


# ─── add steps modal & handler ───────────────────────────────────
@wizard_admin_bp.route("/bundle/<int:bundle_id>/add-steps-modal", methods=["GET"])
@login_required
def add_steps_modal(bundle_id: int):
    bundle = db.get_or_404(WizardBundle, bundle_id)
    # steps not yet in bundle
    existing_ids = {bs.step_id for bs in bundle.steps}  # type: ignore
    available = (
        WizardStep.query.filter(~WizardStep.id.in_(existing_ids))
        .order_by(WizardStep.server_type, WizardStep.position)
        .all()
    )
    return render_template(
        "modals/bundle-add-steps.html", bundle=bundle, steps=available
    )


@wizard_admin_bp.route("/bundle/<int:bundle_id>/add-steps", methods=["POST"])
@login_required
def add_steps(bundle_id: int):
    bundle = db.get_or_404(WizardBundle, bundle_id)
    ids = request.form.getlist("step_ids")
    if not ids:
        abort(400)
    # Determine next position value
    max_pos = (
        db.session.query(func.max(WizardBundleStep.position))
        .filter_by(bundle_id=bundle_id)
        .scalar()
    )
    next_pos = (max_pos or 0) + 1
    for sid in ids:
        try:
            sid_int = int(sid)
        except ValueError:
            continue
        bundle.steps.append(WizardBundleStep(step_id=sid_int, position=next_pos))
        next_pos += 1
    if _commit_or_rollback():
        flash(_("Steps added"), "success")
    if request.headers.get("HX-Request"):
        return list_bundles()
    return redirect(url_for("wizard_admin.list_bundles"))


@wizard_admin_bp.route("/bundle-step/<int:bundle_step_id>/delete", methods=["POST"])
@login_required
def delete_bundle_step(bundle_step_id: int):
    bundle_step = db.get_or_404(WizardBundleStep, bundle_step_id)
    db.session.delete(bundle_step)
    if _commit_or_rollback():
        flash(_("Orphaned step removed"), "success")

    if request.headers.get("HX-Request"):
        return list_bundles()
    return redirect(url_for("wizard_admin.list_bundles"))


# ─── Export/Import functionality ─────────────────────────────────────
@wizard_admin_bp.route("/export/<server_type>", methods=["GET"])
@login_required
def export_server_steps(server_type: str):
    """Export wizard steps for a specific server type as JSON file."""
    try:
        service = WizardExportImportService()
        export_data = service.export_steps_by_server_type(server_type)

        if not export_data.steps:
            flash(
                _("No steps found for server type: {}").format(server_type), "warning"
            )
            if request.headers.get("HX-Request"):
                return list_steps()
            return redirect(url_for("wizard_admin.list_steps"))

        # Create temporary file for download
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as temp_file:
            json.dump(export_data.to_dict(), temp_file, indent=2, ensure_ascii=False)
            temp_file_path = temp_file.name

        # Generate filename with server type and current date
        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        filename = f"wizard_steps_{server_type}_{timestamp}.json"

        return send_file(
            temp_file_path,
            as_attachment=True,
            download_name=filename,
            mimetype="application/json",
        )

    except Exception as e:
        flash(_("Export failed: {}").format(str(e)), "error")
        if request.headers.get("HX-Request"):
            return list_steps()
        return redirect(url_for("wizard_admin.list_steps"))


@wizard_admin_bp.route("/export/bundle/<int:bundle_id>", methods=["GET"])
@login_required
def export_bundle(bundle_id: int):
    """Export a wizard bundle as JSON file."""
    try:
        service = WizardExportImportService()
        export_data = service.export_bundle(bundle_id)

        # Create temporary file for download
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as temp_file:
            json.dump(export_data.to_dict(), temp_file, indent=2, ensure_ascii=False)
            temp_file_path = temp_file.name

        # Generate filename with bundle name and current date
        bundle_name = (
            export_data.bundle.name.replace(" ", "_").lower()
            if export_data.bundle
            else "unknown_bundle"
        )
        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        filename = f"wizard_bundle_{bundle_name}_{timestamp}.json"

        return send_file(
            temp_file_path,
            as_attachment=True,
            download_name=filename,
            mimetype="application/json",
        )

    except ValueError as e:
        flash(_("Export failed: {}").format(str(e)), "error")
        if request.headers.get("HX-Request"):
            return list_bundles()
        return redirect(url_for("wizard_admin.list_bundles"))
    except Exception as e:
        flash(_("Export failed: {}").format(str(e)), "error")
        if request.headers.get("HX-Request"):
            return list_bundles()
        return redirect(url_for("wizard_admin.list_bundles"))


@wizard_admin_bp.route("/import", methods=["GET", "POST"])
@login_required
def import_steps():
    """Import wizard steps from uploaded JSON file."""
    form = WizardImportForm()

    if request.method == "GET":
        # Show import form/modal
        tmpl = (
            "modals/wizard-import-form.html"
            if request.headers.get("HX-Request")
            else "settings/wizard/import_form.html"
        )
        return render_template(tmpl, form=form)

    # POST - handle file upload using form validation
    if not form.validate_on_submit():
        # Form validation failed
        tmpl = (
            "modals/wizard-import-form.html"
            if request.headers.get("HX-Request")
            else "settings/wizard/import_form.html"
        )
        return render_template(tmpl, form=form)

    try:
        # Read and parse JSON
        file = form.file.data
        content = file.read().decode("utf-8")
        import_data = json.loads(content)

        # Check for replace existing flag
        replace_existing = form.replace_existing.data

        # Import data (steps or bundle)
        service = WizardExportImportService()
        result = service.import_data(import_data, replace_existing=replace_existing)

        if result.success:
            success_msg = _("Successfully imported {} items").format(
                result.imported_count
            )
            if result.updated_count > 0:
                success_msg += _(" and updated {} existing items").format(
                    result.updated_count
                )
            flash(success_msg, "success")
        else:
            flash(_("Import failed: {}").format(result.message), "error")
            for error in result.errors:
                flash(error, "error")

    except json.JSONDecodeError:
        flash(_("Invalid JSON file"), "error")
    except Exception as e:
        flash(_("Import failed: {}").format(str(e)), "error")

    # Return updated view
    if request.headers.get("HX-Request"):
        return list_steps()
    return redirect(url_for("wizard_admin.list_steps"))


@wizard_admin_bp.route("/reset/<server_type>", methods=["POST"])
@login_required
def reset_server_steps(server_type: str):
    """Reset wizard steps to defaults for a specific server type.

    This resets BOTH pre_invite and post_invite categories:
    - pre_invite: Deletes all custom pre_invite steps (no defaults to reimport)
    - post_invite: Deletes all custom post_invite steps and reimports from YAML
    """
    from app.services.wizard_reset import WizardResetService

    service = WizardResetService()

    # Track overall success and collect counts
    total_deleted = 0
    total_imported = 0
    errors = []

    # 1. Delete pre_invite steps (no defaults exist for pre_invite)
    try:
        pre_deleted = WizardStep.query.filter_by(
            server_type=server_type, category="pre_invite"
        ).delete()
        total_deleted += pre_deleted
        db.session.flush()
    except Exception as e:
        errors.append(f"Failed to delete pre_invite steps: {e!s}")
        db.session.rollback()

    # 2. Reset post_invite steps (delete and reimport from YAML defaults)
    try:
        success, message, count = service.reset_server_steps(
            server_type, category="post_invite"
        )

        if success:
            total_imported += count
            # Extract deleted count from message if available
            # Message format: "Reset X steps for Y (deleted Z, imported W)"
            import re

            match = re.search(r"deleted (\d+)", message)
            if match:
                total_deleted += int(match.group(1))
        else:
            errors.append(message)
    except Exception as e:
        errors.append(f"Failed to reset post_invite steps: {e!s}")
        db.session.rollback()

    # Commit all changes if no errors
    if not errors:
        try:
            db.session.commit()
            flash(
                _("Reset {} steps for {} (deleted {}, imported {})").format(
                    server_type,
                    server_type.capitalize(),
                    total_deleted,
                    total_imported,
                ),
                "success",
            )
        except Exception as e:
            db.session.rollback()
            flash(_("Failed to reset steps: {}").format(str(e)), "error")
    else:
        # Show error messages
        for error in errors:
            flash(error, "error")

    # Return updated view
    if request.headers.get("HX-Request"):
        return list_steps()
    return redirect(url_for("wizard_admin.list_steps"))
