from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_babel import _
from flask_login import current_user, login_required

from app.blueprints.admin.routes import admin_bp
from app.extensions import db
from app.forms.admin import AdminCreateForm, AdminUpdateForm
from app.models import AdminAccount, WebAuthnCredential

admin_accounts_bp = Blueprint("admin_accounts", __name__, url_prefix="/settings/admins")


@admin_accounts_bp.route("", methods=["GET"])
@login_required
def list_admins():
    """Render list of admin accounts."""
    admins = AdminAccount.query.order_by(AdminAccount.username).all()
    if request.headers.get("HX-Request"):
        return render_template("settings/admins.html", admins=admins)
    return render_template("settings/admins.html", admins=admins)


# ── Create ─────────────────────────────────────────────────────────────
@admin_accounts_bp.route("/create", methods=["GET", "POST"])
@login_required
def create_admin():
    form = AdminCreateForm()
    if form.validate_on_submit():
        if AdminAccount.query.filter_by(username=form.username.data).first():
            form.username.errors = list(form.username.errors) + [
                "Username already exists."
            ]
        else:
            acc = AdminAccount()
            acc.username = form.username.data
            if form.password.data:
                acc.set_password(form.password.data)
            db.session.add(acc)
            db.session.commit()
            flash(_("Admin created"), "success")
            return redirect(url_for("admin_accounts.list_admins"))
    # GET or POST-with-errors: render modal
    if request.headers.get("HX-Request"):
        return render_template("modals/create-admin.html", form=form)
    return render_template("modals/create-admin.html", form=form)


# ── Edit ───────────────────────────────────────────────────────────────
@admin_accounts_bp.route("/<int:admin_id>/edit", methods=["GET", "POST"])
@login_required
def edit_admin(admin_id):
    acc = AdminAccount.query.get_or_404(admin_id)
    form = AdminUpdateForm(obj=acc)
    if form.validate_on_submit():
        # Username uniqueness check
        other = AdminAccount.query.filter_by(username=form.username.data).first()
        if other and other.id != acc.id:
            form.username.errors = list(form.username.errors) + [
                "Username already taken"
            ]
        else:
            acc.username = form.username.data
            if form.password.data:
                acc.set_password(form.password.data)
            db.session.commit()
            flash(_("Admin updated"), "success")
            return redirect(url_for("admin_accounts.list_admins"))
    if request.headers.get("HX-Request"):
        return render_template("modals/edit-admin.html", form=form, admin=acc)
    return render_template("modals/edit-admin.html", form=form, admin=acc)


# ── Delete ─────────────────────────────────────────────────────────────
@admin_accounts_bp.route("/", methods=["DELETE"])
@login_required
def delete_admin():
    """Delete an admin account and return updated list for HTMX requests."""
    admin_id = request.args.get("delete")

    if admin_id:
        # Use synchronize_session=False for performance; no loaded objects are in session
        AdminAccount.query.filter_by(id=int(admin_id)).delete(synchronize_session=False)
        db.session.commit()

    # If the request came from HTMX, send back the refreshed admins partial so the
    # client can swap it in seamlessly (keeping the UI in sync without a full page reload).
    if request.headers.get("HX-Request"):
        admins = AdminAccount.query.order_by(AdminAccount.username).all()
        return render_template("settings/admins.html", admins=admins)

    # Non-HTMX fall-back: redirect back to the list page
    return redirect(url_for("admin_accounts.list_admins"))


# Add a route for user profile that's not under the settings prefix


@admin_bp.route("/profile", methods=["GET"])
@login_required
def user_profile():
    """Render user profile page."""
    return render_template("profile.html")


@admin_bp.route("/profile/change-password", methods=["POST"])
@login_required
def change_password():
    """Change user password with HTMX response."""

    if not isinstance(current_user, AdminAccount):
        return render_template(
            "components/password_result.html",
            error="Only admin accounts can change passwords",
        )

    current_password = request.form.get("current_password")
    new_password = request.form.get("new_password")
    confirm_password = request.form.get("confirm_password")

    # Validation
    if not current_password or not new_password or not confirm_password:
        return render_template(
            "components/password_result.html", error="All password fields are required"
        )

    if new_password != confirm_password:
        return render_template(
            "components/password_result.html", error="New passwords do not match"
        )

    if not current_user.check_password(current_password):
        return render_template(
            "components/password_result.html", error="Current password is incorrect"
        )

    if len(new_password) < 6:
        return render_template(
            "components/password_result.html",
            error="New password must be at least 6 characters long",
        )

    try:
        current_user.set_password(new_password)
        db.session.commit()
        return render_template(
            "components/password_result.html", success="Password changed successfully"
        )
    except Exception:
        db.session.rollback()
        return render_template(
            "components/password_result.html", error="Failed to change password"
        )


@admin_accounts_bp.route("/<int:admin_id>/reset-passkeys", methods=["POST"])
@login_required
def reset_passkeys(admin_id):
    """Reset all passkeys for a specific admin account."""
    admin = AdminAccount.query.get_or_404(admin_id)

    try:
        # Delete all passkeys for this admin
        WebAuthnCredential.query.filter_by(admin_account_id=admin_id).delete()
        db.session.commit()
        flash(
            _("All passkeys for {} have been reset").format(admin.username), "success"
        )
    except Exception:
        db.session.rollback()
        flash(_("Failed to reset passkeys for {}").format(admin.username), "error")

    return redirect(url_for("admin_accounts.list_admins"))


@admin_accounts_bp.route("/<int:admin_id>/passkeys", methods=["GET"])
@login_required
def admin_passkeys(admin_id):
    """View passkeys for a specific admin account."""
    admin = AdminAccount.query.get_or_404(admin_id)
    passkeys = WebAuthnCredential.query.filter_by(admin_account_id=admin_id).all()

    if request.headers.get("HX-Request"):
        return render_template(
            "components/admin_passkeys.html", admin=admin, passkeys=passkeys
        )
    return render_template(
        "components/admin_passkeys.html", admin=admin, passkeys=passkeys
    )
