import hashlib
import secrets

import structlog
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_babel import _
from flask_login import current_user, login_required

from app.extensions import db
from app.forms.api_keys import ApiKeyCreateForm
from app.models import AdminAccount, AdminUser, ApiKey

api_keys_bp = Blueprint("api_keys", __name__, url_prefix="/settings/api-keys")

logger = structlog.get_logger("wizarr.api_keys")


@api_keys_bp.route("", methods=["GET"])
@login_required
def list_api_keys():
    """Display list of API keys."""
    api_keys = (
        ApiKey.query.filter_by(is_active=True).order_by(ApiKey.created_at.desc()).all()
    )

    if request.headers.get("HX-Request"):
        return render_template("partials/api_keys_grid.html", api_keys=api_keys)
    return render_template("settings/api_keys.html", api_keys=api_keys)


@api_keys_bp.route("/create", methods=["GET", "POST"])
@login_required
def create_api_key():
    """Create a new API key."""
    form = ApiKeyCreateForm()
    raw_key = None

    if form.validate_on_submit():
        # Check if name already exists
        existing = ApiKey.query.filter_by(name=form.name.data, is_active=True).first()
        if existing:
            form.name.errors = [
                *list(form.name.errors),
                "API key with this name already exists.",
            ]
        else:
            # Resolve the integer FK for created_by_id.
            # The legacy AdminUser has id="admin" (a string) and is not an
            # ORM row, so we must look up the first real AdminAccount instead.
            if isinstance(current_user, AdminUser):
                admin_account = AdminAccount.query.first()
                if admin_account is None:
                    flash(
                        _(
                            "No admin account found. Please set up a proper admin account before creating API keys."
                        ),
                        "error",
                    )
                    return redirect(url_for("api_keys.list_api_keys"))
                created_by_id: int = admin_account.id
            else:
                created_by_id = current_user.id

            # Generate a secure random API key
            raw_key = secrets.token_urlsafe(32)
            key_hash = hashlib.sha256(raw_key.encode()).hexdigest()

            # Create API key record
            api_key = ApiKey(
                name=form.name.data,
                key_hash=key_hash,
                created_by_id=created_by_id,
                is_active=True,
            )

            try:
                db.session.add(api_key)
                db.session.commit()
            except Exception:
                db.session.rollback()
                logger.exception(
                    "Failed to create API key",
                    name=form.name.data,
                    admin=current_user.username,
                )
                flash(_("Failed to create API key due to a database error."), "error")
                return redirect(url_for("api_keys.list_api_keys"))

            logger.info(
                "Created new API key",
                name=form.name.data,
                admin=current_user.username,
            )
            flash(
                _(
                    "API key created successfully. Please copy it now as it won't be shown again."
                ),
                "success",
            )

            # Return the form with the raw key for display
            if request.headers.get("HX-Request"):
                return render_template(
                    "modals/create-api-key.html",
                    form=form,
                    raw_key=raw_key,
                    api_key=api_key,
                )
            return render_template(
                "modals/create-api-key.html",
                form=form,
                raw_key=raw_key,
                api_key=api_key,
            )

    # GET or POST-with-errors: render modal
    if request.headers.get("HX-Request"):
        return render_template("modals/create-api-key.html", form=form, raw_key=raw_key)
    return render_template("modals/create-api-key.html", form=form, raw_key=raw_key)


@api_keys_bp.route("/<int:key_id>/delete", methods=["POST", "DELETE"])
@login_required
def delete_api_key(key_id):
    """Delete an API key."""
    api_key = ApiKey.query.get_or_404(key_id)

    # Soft delete by marking as inactive
    api_key.is_active = False
    db.session.commit()

    logger.info(
        "Deleted API key '%s' (ID: %d) by admin %s",
        api_key.name,
        key_id,
        current_user.username,
    )
    flash(_("API key deleted successfully"), "success")

    # If it's an HTMX request, return the updated grid
    if request.headers.get("HX-Request"):
        api_keys = (
            ApiKey.query.filter_by(is_active=True)
            .order_by(ApiKey.created_at.desc())
            .all()
        )
        return render_template("partials/api_keys_grid.html", api_keys=api_keys)

    return redirect(url_for("api_keys.list_api_keys"))
