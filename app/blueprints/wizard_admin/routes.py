from __future__ import annotations

import re
from typing import cast

from flask import (
    Blueprint,
    abort,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_babel import gettext as _
from flask_login import login_required
from sqlalchemy import func

from app.extensions import db
from app.forms.wizard import (
    SimpleWizardStepForm,
    WizardBundleForm,
    WizardPresetForm,
    WizardStepForm,
)
from app.models import MediaServer, WizardBundle, WizardBundleStep, WizardStep
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

# Matches {{ _( "Some text" ) }} or {{ _( 'Some text' ) }} with arbitrary
# whitespace.
_I18N_PATTERN = re.compile(r"{{\s*_\(\s*(['\"])(.*?)\1\s*\)\s*}}", re.DOTALL)


def _strip_localization(md: str) -> str:
    """Remove Jinja gettext wrappers from markdown, leaving plain text."""
    return _I18N_PATTERN.sub(lambda m: m.group(2), md)


@wizard_admin_bp.route("/", methods=["GET"])
@login_required
def list_steps():
    # Group steps by server_type for display
    rows = (
        # Exclude custom steps (managed via Wizard Bundles) from the default view
        WizardStep.query.filter(WizardStep.server_type != "custom")
        .order_by(WizardStep.server_type, WizardStep.position)
        .all()
    )
    grouped: dict[str, list[WizardStep]] = {}
    for row in rows:
        grouped.setdefault(row.server_type, []).append(row)

    # Filter: show only servers that are currently configured/enabled
    active_types = {srv.server_type for srv in MediaServer.query.all()}
    grouped = {
        stype: steps for stype, steps in grouped.items() if stype in active_types
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
        db.session.commit()
        flash(_("Cleaned up {} orphaned step(s)").format(len(orphaned_steps)), "info")

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

        max_pos = (
            db.session.query(func.max(WizardStep.position))
            .filter_by(server_type=stype)
            .scalar()
        )
        next_pos = (max_pos or 0) + 1

        cleaned_md = _strip_localization(form.markdown.data or "")

        step = WizardStep(
            server_type=stype,
            position=next_pos,
            title=getattr(form, "title", None) and form.title.data or None,
            markdown=cleaned_md,
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

        db.session.commit()
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

            # Find next position for this server type
            max_pos = (
                db.session.query(func.max(WizardStep.position))
                .filter_by(server_type=server_type)
                .scalar()
            )
            next_pos = (max_pos or 0) + 1

            # Create the step
            step = WizardStep(
                server_type=server_type,
                position=next_pos,
                title=title,
                markdown=markdown_content,
            )
            db.session.add(step)
            db.session.commit()

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
    step = WizardStep.query.get_or_404(step_id)

    simple = step.server_type == "custom"
    FormCls = SimpleWizardStepForm if simple else WizardStepForm
    form = FormCls(request.form if request.method == "POST" else None, obj=step)

    if form.validate_on_submit():
        if not simple:
            server_type_attr = getattr(form, "server_type", None)
            step.server_type = server_type_attr.data if server_type_attr else "custom"

        step.title = getattr(form, "title", None) and form.title.data or None
        cleaned_md = _strip_localization(form.markdown.data or "")
        step.markdown = cleaned_md

        db.session.commit()
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
    step = WizardStep.query.get_or_404(step_id)

    # Check if this is a custom step (from bundle context)
    is_custom_step = step.server_type == "custom"

    db.session.delete(step)
    db.session.commit()
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
    """Accept JSON array of step IDs in new order for a given server_type."""
    order_raw = request.json
    if not isinstance(order_raw, list):
        abort(400)
    order = cast(list[int], order_raw)

    rows = WizardStep.query.filter(WizardStep.id.in_(order)).all()
    id_to_row = {r.id: r for r in rows}

    # ------------------------------------------------------------------
    # Phase 1: assign *temporary* negative positions to avoid violating the
    # unique (server_type, position) constraint during in-place updates.
    # ------------------------------------------------------------------
    for tmp_pos, step_id in enumerate(order, start=1):
        row = id_to_row.get(step_id)
        if row is None:
            continue
        row.position = -tmp_pos  # e.g. -1, -2, … distinct & negative

    db.session.flush()  # issues UPDATEs but keeps transaction open

    # ------------------------------------------------------------------
    # Phase 2: set final 0-based positions
    # ------------------------------------------------------------------
    for final_pos, step_id in enumerate(order):
        row = id_to_row.get(step_id)
        if row is None:
            continue
        row.position = final_pos

    db.session.commit()
    return jsonify({"status": "ok"})


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
        db.session.commit()
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
    bundle = WizardBundle.query.get_or_404(bundle_id)
    form = WizardBundleForm(
        request.form if request.method == "POST" else None, obj=bundle
    )

    if form.validate_on_submit():
        bundle.name = form.name.data
        bundle.description = form.description.data or None
        db.session.commit()
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
    bundle = WizardBundle.query.get_or_404(bundle_id)
    db.session.delete(bundle)
    db.session.commit()
    flash(_("Bundle deleted"), "success")

    if request.headers.get("HX-Request"):
        return list_bundles()
    return redirect(url_for("wizard_admin.list_bundles"))


@wizard_admin_bp.route("/bundle/<int:bundle_id>/reorder", methods=["POST"])
@login_required
def reorder_bundle(bundle_id: int):
    order_raw = request.json  # expects list of step IDs in new order
    if not isinstance(order_raw, list):
        abort(400)
    order = cast(list[int], order_raw)

    rows = WizardBundleStep.query.filter(
        WizardBundleStep.bundle_id == bundle_id,
        WizardBundleStep.step_id.in_(order),
    ).all()
    id_to_row = {r.step_id: r for r in rows}

    # Phase 1 – temporary negative positions to satisfy unique constraint
    for tmp_pos, step_id in enumerate(order, start=1):
        row = id_to_row.get(step_id)
        if row is None:
            continue
        row.position = -tmp_pos
    db.session.flush()

    # Phase 2 – final 0-based positions
    for final_pos, step_id in enumerate(order):
        row = id_to_row.get(step_id)
        if row is None:
            continue
        row.position = final_pos
    db.session.commit()
    return jsonify({"status": "ok"})


# ─── add steps modal & handler ───────────────────────────────────
@wizard_admin_bp.route("/bundle/<int:bundle_id>/add-steps-modal", methods=["GET"])
@login_required
def add_steps_modal(bundle_id: int):
    bundle = WizardBundle.query.get_or_404(bundle_id)
    # steps not yet in bundle
    existing_ids = {bs.step_id for bs in bundle.steps}
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
    bundle = WizardBundle.query.get_or_404(bundle_id)
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
    db.session.commit()
    flash(_("Steps added"), "success")
    if request.headers.get("HX-Request"):
        return list_bundles()
    return redirect(url_for("wizard_admin.list_bundles"))


@wizard_admin_bp.route("/bundle-step/<int:bundle_step_id>/delete", methods=["POST"])
@login_required
def delete_bundle_step(bundle_step_id: int):
    bundle_step = WizardBundleStep.query.get_or_404(bundle_step_id)
    db.session.delete(bundle_step)
    db.session.commit()
    flash(_("Orphaned step removed"), "success")

    if request.headers.get("HX-Request"):
        return list_bundles()
    return redirect(url_for("wizard_admin.list_bundles"))
