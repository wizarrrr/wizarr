from flask import Blueprint, render_template, abort
from jinja2 import TemplateNotFound

from app.security import logged_out_required

authentication = Blueprint("auth", __name__, template_folder="../views/authentication/")

@authentication.route("/login")
@logged_out_required()
def login_route():
    return render_template("login.html")

@authentication.route("/forgot-password")
@logged_out_required()
def forgot_password_route():
    return render_template("forgot-password.html")
