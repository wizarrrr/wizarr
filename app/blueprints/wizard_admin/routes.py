from __future__ import annotations

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, abort
from flask_login import login_required
from sqlalchemy import func
import re

from app.extensions import db
from app.models import WizardStep, WizardBundle, WizardBundleStep
from app.forms.wizard import WizardStepForm, WizardBundleForm

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
        WizardStep.query
        .order_by(WizardStep.server_type, WizardStep.position)
        .all()
    )
    grouped: dict[str, list[WizardStep]] = {}
    for row in rows:
        grouped.setdefault(row.server_type, []).append(row)

    # ── fetch bundles ─────────────────────────────────────────────
    bundles = (
        WizardBundle.query
        .order_by(WizardBundle.id)
        .all()
    )

    # When requested via HTMX we return only the inner fragment that is meant
    # to be swapped into the <div id="tab-body"> container on the settings
    # page.  For a normal full-page navigation we extend the base layout so
    # the <head> section is populated and styling/scripts remain intact.
    tmpl = (
        "settings/wizard/index.html"
        if request.headers.get("HX-Request")
        else "settings/page.html"  # fallback renders full settings page
    )

    # For the full page fallback we have to render the *entire* settings page
    # with the wizard tab pre-selected.  Rather than duplicating that layout
    # we reuse the existing generic settings page helper and pass a query
    # parameter that the template looks for to auto-open the correct tab.
    if tmpl == "settings/page.html":
        return redirect(url_for("settings.page") + "#wizard")

    return render_template(tmpl, grouped=grouped, bundles=bundles)


@wizard_admin_bp.route("/create", methods=["GET", "POST"])
@login_required
def create_step():
    form = WizardStepForm(request.form if request.method == "POST" else None)

    if form.validate_on_submit():
        # Determine next position within this server_type
        max_pos = (
            db.session.query(func.max(WizardStep.position))
            .filter_by(server_type=form.server_type.data)
            .scalar()
        )
        next_pos = (max_pos or 0) + 1

        cleaned_md = _strip_localization(form.markdown.data)

        step = WizardStep(
            server_type=form.server_type.data,
            position=next_pos,
            title=form.title.data or None,
            markdown=cleaned_md,
            requires=[s.strip() for s in (form.requires.data or "").split(",") if s.strip()],
        )
        db.session.add(step)
        db.session.commit()
        flash("Step created", "success")
        return redirect(url_for("wizard_admin.list_steps"))

    # GET – render modal. If HTMX, serve modal partial; otherwise fallback full page.
    tmpl = (
        "modals/wizard-step-form.html"
        if request.headers.get("HX-Request")
        else "settings/wizard/form.html"
    )
    return render_template(tmpl, form=form, action="create")


@wizard_admin_bp.route("/<int:step_id>/edit", methods=["GET", "POST"])
@login_required
def edit_step(step_id: int):
    step = WizardStep.query.get_or_404(step_id)
    form = WizardStepForm(request.form if request.method == "POST" else None, obj=step)

    if form.validate_on_submit():
        step.server_type = form.server_type.data
        step.title = form.title.data or None
        cleaned_md = _strip_localization(form.markdown.data)
        step.markdown = cleaned_md
        step.requires = [s.strip() for s in (form.requires.data or "").split(",") if s.strip()]
        db.session.commit()
        flash("Step updated", "success")
        return redirect(url_for("wizard_admin.list_steps"))

    # Prepopulate requires comma list for GET
    if request.method == "GET":
        form.requires.data = ", ".join(step.requires or [])
        # Pre-fill markdown stripped of localization for a cleaner editing exp.
        form.markdown.data = _strip_localization(step.markdown)

    tmpl = (
        "modals/wizard-step-form.html"
        if request.headers.get("HX-Request")
        else "settings/wizard/form.html"
    )
    return render_template(tmpl, form=form, action="edit", step=step)


@wizard_admin_bp.route("/<int:step_id>/delete", methods=["POST"])
@login_required
def delete_step(step_id: int):
    step = WizardStep.query.get_or_404(step_id)
    db.session.delete(step)
    db.session.commit()
    flash("Step deleted", "success")

    # For HTMX requests return the updated steps list fragment so the client
    # can refresh the table without a full page reload. Otherwise fall back
    # to a normal redirect which lands on the full settings page (wizard tab
    # pre-selected) to keep the UI consistent and fully styled.
    if request.headers.get("HX-Request"):
        return list_steps()

    return redirect(url_for("settings.page") + "#wizard")


@wizard_admin_bp.route("/reorder", methods=["POST"])
@login_required
def reorder_steps():
    """Accept JSON array of step IDs in new order for a given server_type."""
    order = request.json
    if not isinstance(order, list):
        abort(400)

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
    html = md_to_html(raw, extensions=["fenced_code", "tables", "attr_list"])
    return html


# ─── bundle CRUD ─────────────────────────────────────────────────
@wizard_admin_bp.route("/bundle/create", methods=["GET", "POST"])
@login_required
def create_bundle():
    form = WizardBundleForm(request.form if request.method == "POST" else None)

    if form.validate_on_submit():
        bundle = WizardBundle(name=form.name.data, description=form.description.data or None)
        db.session.add(bundle)
        db.session.commit()
        flash("Bundle created", "success")
        return redirect(url_for("wizard_admin.list_steps"))

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
    form = WizardBundleForm(request.form if request.method == "POST" else None, obj=bundle)

    if form.validate_on_submit():
        bundle.name = form.name.data
        bundle.description = form.description.data or None
        db.session.commit()
        flash("Bundle updated", "success")
        return redirect(url_for("wizard_admin.list_steps"))

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
    flash("Bundle deleted", "success")

    if request.headers.get("HX-Request"):
        return list_steps()
    return redirect(url_for("settings.page") + "#wizard")


@wizard_admin_bp.route("/bundle/<int:bundle_id>/reorder", methods=["POST"])
@login_required
def reorder_bundle(bundle_id: int):
    order = request.json  # expects list of step IDs in new order
    if not isinstance(order, list):
        abort(400)

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
        WizardStep.query
        .filter(~WizardStep.id.in_(existing_ids))
        .order_by(WizardStep.server_type, WizardStep.position)
        .all()
    )
    return render_template("modals/bundle-add-steps.html", bundle=bundle, steps=available)


@wizard_admin_bp.route("/bundle/<int:bundle_id>/add-steps", methods=["POST"])
@login_required
def add_steps(bundle_id: int):
    bundle = WizardBundle.query.get_or_404(bundle_id)
    ids = request.form.getlist("step_ids")
    if not ids:
        abort(400)
    # Determine next position value
    max_pos = db.session.query(func.max(WizardBundleStep.position)).filter_by(bundle_id=bundle_id).scalar()
    next_pos = (max_pos or 0) + 1
    for sid in ids:
        try:
            sid_int = int(sid)
        except ValueError:
            continue
        bundle.steps.append(
            WizardBundleStep(step_id=sid_int, position=next_pos)
        )
        next_pos += 1
    db.session.commit()
    flash("Steps added", "success")
    if request.headers.get("HX-Request"):
        return list_steps()
    return redirect(url_for("wizard_admin.list_steps")) 