from flask import Blueprint, render_template, request, redirect, url_for, flash, make_response
from flask_login import login_required

from app.extensions import db
from app.models import AdminAccount
from app.forms.admin import AdminCreateForm, AdminUpdateForm

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
            form.username.errors.append("Username already exists.")
        else:
            acc = AdminAccount(username=form.username.data)
            acc.set_password(form.password.data)
            db.session.add(acc)
            db.session.commit()
            flash("Admin created", "success")
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
            form.username.errors.append("Username already taken")
        else:
            acc.username = form.username.data
            if form.password.data:
                acc.set_password(form.password.data)
            db.session.commit()
            flash("Admin updated", "success")
            return redirect(url_for("admin_accounts.list_admins"))
    if request.headers.get("HX-Request"):
        return render_template("modals/edit-admin.html", form=form, admin=acc)
    return render_template("modals/edit-admin.html", form=form, admin=acc)


# ── Delete ─────────────────────────────────────────────────────────────
@admin_accounts_bp.route("/", methods=["DELETE"])
@login_required
def delete_admin():
    admin_id = request.args.get("delete")
    if admin_id:
        AdminAccount.query.filter_by(id=int(admin_id)).delete(synchronize_session=False)
        db.session.commit()
    return "", 204 