from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.forms.signup import (
    ReviewSignupForm,
    SignupActionForm,
    SignupForm,
    SignupSettingsForm,
)
from app.models import MediaServer, Settings, SignupRequest
from app.services.signup import (
    approve_request,
    notify_owner,
    reject_request,
    send_approval,
    signup_enabled,
    submit_request,
)

signup_bp = Blueprint("signup", __name__)


@signup_bp.after_request
def private_response(response):
    response.headers["Cache-Control"] = "no-store"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-Robots-Tag"] = "noindex, nofollow"
    return response


@signup_bp.route("/signup", methods=["GET", "POST"])
def signup():
    if not signup_enabled():
        abort(404)
    form = SignupForm()
    if form.validate_on_submit():
        if not form.website.data:
            try:
                item = submit_request(
                    form.name.data,
                    form.email.data,
                    form.message.data or "",
                    request.remote_addr or "unknown",
                )
            except IntegrityError:
                db.session.rollback()
                item = None
            except ValueError as exc:
                status = 429 if str(exc) == "rate_limit" else 503
                return render_template(
                    "signup/request.html", form=form, busy=True
                ), status
            if item:
                try:
                    notify_owner(item)
                except (ValueError, OSError) as exc:
                    current_app.logger.warning(
                        "Signup owner notification failed (%s)", type(exc).__name__
                    )
        return redirect(url_for("signup.submitted"), code=303)
    status = 400 if request.method == "POST" else 200
    return render_template("signup/request.html", form=form), status


@signup_bp.get("/signup/submitted")
def submitted():
    if not signup_enabled():
        abort(404)
    return render_template("signup/submitted.html")


@signup_bp.route("/admin/signups", methods=["GET", "POST"])
@login_required
def admin():
    settings_form = SignupSettingsForm()
    if settings_form.validate_on_submit():
        row = Settings.query.filter_by(key="public_signup_enabled").first()
        if row is None:
            row = Settings(key="public_signup_enabled")
            db.session.add(row)
        row.value = "true" if settings_form.enabled.data else "false"
        db.session.commit()
        flash("Access request settings saved.", "success")
        return redirect(url_for("signup.admin"), code=303)
    if request.method == "POST":
        abort(400)
    settings_form.enabled.data = signup_enabled()
    review_form = ReviewSignupForm()
    review_form.server_id.choices = [
        (s.id, s.name) for s in MediaServer.query.filter_by(verified=True).all()
    ]
    page = max(1, request.args.get("page", 1, type=int))
    requests_page = SignupRequest.query.order_by(
        SignupRequest.created_at.desc()
    ).paginate(page=page, per_page=25, error_out=False)
    return render_template(
        "signup/admin.html",
        settings_form=settings_form,
        review_form=review_form,
        action_form=SignupActionForm(),
        requests_page=requests_page,
    )


@signup_bp.post("/admin/signups/<int:item_id>/<action>")
@login_required
def review(item_id, action):
    item = db.get_or_404(SignupRequest, item_id)
    form = ReviewSignupForm() if action == "approve" else SignupActionForm()
    if action == "approve":
        form.server_id.choices = [
            (s.id, s.name) for s in MediaServer.query.filter_by(verified=True).all()
        ]
    if not form.validate_on_submit():
        abort(400)
    try:
        if action == "approve":
            item = approve_request(item_id, form.server_id.data, current_user.username)
        elif action == "reject":
            if not reject_request(item_id, current_user.username):
                raise ValueError("This request has already been reviewed.")
            flash("Request rejected. No account was created.", "success")
            return redirect(url_for("signup.admin"), code=303)
        elif action != "resend":
            abort(404)
        send_approval(item)
        flash("Approved. The personal signup link has been emailed.", "success")
    except (ValueError, OSError) as exc:
        db.session.rollback()
        current_app.logger.warning(
            "Signup review or delivery failed (%s)", type(exc).__name__
        )
        flash(
            "Could not complete the action or deliver the email. Check the request status and email configuration; approved requests can retry email delivery.",
            "error",
        )
    return redirect(url_for("signup.admin"), code=303)
