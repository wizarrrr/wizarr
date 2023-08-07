from flask import Blueprint, render_template, request
from jinja2 import TemplateNotFound

from app.security import login_required_unless_setup

modals = Blueprint("modals", __name__, template_folder="../views/modals/")

@modals.get("/partials/modals/<string:subpath>")
@login_required_unless_setup()
def modals_partials(subpath, **kwargs):
    # Get all form and post data
    form = request.form if request.form else {}
    post = request.args if request.args else {}
    args = kwargs if kwargs else {}

    # Merge form and post data
    data = {**form, **post, **args}

    return render_template("modal.html", subpath=f"{subpath}.html", **data)
