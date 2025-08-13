from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_babel import gettext as _
from flask_login import login_required

from app.extensions import db
from app.forms.connections import ConnectionForm
from app.models import Connection

connections_bp = Blueprint("connections", __name__, url_prefix="/settings/connections")


@connections_bp.route("/", methods=["GET"])
@login_required
def list_connections():
    """List all connections."""
    connections = (
        Connection.query.join(Connection.media_server).order_by(Connection.name).all()
    )

    if request.headers.get("HX-Request"):
        return render_template("settings/connections.html", connections=connections)
    return redirect(url_for("settings.page") + "#connections")


@connections_bp.route("/create", methods=["GET", "POST"])
@login_required
def create_connection():
    """Create a new connection."""
    form = ConnectionForm()

    # Pre-select connection type if provided
    connection_type = request.args.get("connection_type") or request.form.get(
        "connection_type"
    )
    if connection_type and request.method == "GET":
        form.connection_type.data = connection_type

    if form.validate_on_submit():
        connection = Connection(
            connection_type=form.connection_type.data,
            name=form.name.data,
            url=form.url.data,
            api_key=form.api_key.data,
            media_server_id=form.media_server_id.data,
        )
        db.session.add(connection)
        db.session.commit()

        flash(_("Connection created successfully!"), "success")

        if request.headers.get("HX-Request"):
            return list_connections()
        return redirect(url_for("connections.list_connections"))

    modal_tmpl = "modals/connection-form.html"
    page_tmpl = "settings/connections/form.html"
    tmpl = modal_tmpl if request.headers.get("HX-Request") else page_tmpl

    return render_template(tmpl, form=form, action="create")


@connections_bp.route("/<int:connection_id>/edit", methods=["GET", "POST"])
@login_required
def edit_connection(connection_id: int):
    """Edit an existing connection."""
    connection = Connection.query.get_or_404(connection_id)
    form = ConnectionForm(obj=connection)

    if form.validate_on_submit():
        connection.connection_type = form.connection_type.data
        connection.name = form.name.data
        connection.url = form.url.data
        connection.api_key = form.api_key.data
        connection.media_server_id = form.media_server_id.data

        db.session.commit()

        flash(_("Connection updated successfully!"), "success")

        if request.headers.get("HX-Request"):
            return list_connections()
        return redirect(url_for("connections.list_connections"))

    modal_tmpl = "modals/connection-form.html"
    page_tmpl = "settings/connections/form.html"
    tmpl = modal_tmpl if request.headers.get("HX-Request") else page_tmpl

    return render_template(tmpl, form=form, action="edit", connection=connection)


@connections_bp.route("/<int:connection_id>/delete", methods=["POST"])
@login_required
def delete_connection(connection_id: int):
    """Delete a connection."""
    connection = Connection.query.get_or_404(connection_id)

    db.session.delete(connection)
    db.session.commit()

    flash(_("Connection deleted successfully!"), "success")

    if request.headers.get("HX-Request"):
        return list_connections()
    return redirect(url_for("connections.list_connections"))
