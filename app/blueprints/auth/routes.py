from flask import Blueprint, render_template, request, redirect, session, url_for
from werkzeug.security import check_password_hash
from app.models import Settings, AdminUser
from app.extensions import db
import os, logging
from flask_babel import _
from flask_login import login_user

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
   
    if os.getenv("DISABLE_BUILTIN_AUTH", "").lower() == "true":
        login_user(AdminUser(), remember=bool(request.form.get("remember")))
        return redirect("/")

    if request.method == "GET":
        return render_template("login.html")

    username = request.form.get("username")
    password = request.form.get("password")

    # fetch the stored admin credentials
    admin_username = (
        db.session
          .query(Settings.value)
          .filter_by(key="admin_username")
          .scalar()
    )
    admin_password_hash = (
        db.session
          .query(Settings.value)
          .filter_by(key="admin_password")
          .scalar()
    )

    if username == admin_username and check_password_hash(admin_password_hash, password):
        # ❑ auto-migrate sha256 → scrypt
        login_user(AdminUser(), remember=bool(request.form.get("remember")))
        return redirect("/")

    logging.warning("Failed login for user %s", username)
    return render_template("login.html", error=_("Invalid username or password"))
