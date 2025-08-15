from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_babel import gettext as _
from flask_login import login_required

from app.extensions import db
from app.forms.connections import ConnectionForm
from app.models import Connection
from app.services.companions import get_companion_client

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
        # Test the connection before saving
        test_connection = Connection(
            connection_type=form.connection_type.data,
            name=form.name.data,
            url=form.url.data,
            api_key=form.api_key.data,
            media_server_id=form.media_server_id.data,
        )

        try:
            connection_type = form.connection_type.data
            if not connection_type:
                flash(_("Connection type is required"), "error")
                modal_tmpl = "modals/connection-form.html"
                page_tmpl = "settings/connections/form.html"
                tmpl = modal_tmpl if request.headers.get("HX-Request") else page_tmpl
                return render_template(tmpl, form=form, action="create")

            client_class = get_companion_client(connection_type)
            client = client_class()
            test_result = client.test_connection(test_connection)

            if test_result["status"] == "error":
                flash(
                    _(
                        "Connection test failed: %(message)s",
                        message=test_result["message"],
                    ),
                    "error",
                )
                modal_tmpl = "modals/connection-form.html"
                page_tmpl = "settings/connections/form.html"
                tmpl = modal_tmpl if request.headers.get("HX-Request") else page_tmpl
                return render_template(tmpl, form=form, action="create")
            if test_result["status"] == "success":
                flash(_("Connection test successful!"), "info")
        except ValueError:
            # Unknown connection type - this shouldn't happen due to form validation
            flash(_("Unknown connection type"), "error")
            modal_tmpl = "modals/connection-form.html"
            page_tmpl = "settings/connections/form.html"
            tmpl = modal_tmpl if request.headers.get("HX-Request") else page_tmpl
            return render_template(tmpl, form=form, action="create")

        # Save the connection
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


@connections_bp.route("/test", methods=["POST"])
@login_required
def test_connection():
    """Test a connection without saving it."""
    form = ConnectionForm()

    if not form.validate_on_submit():
        # Check if it's just a CSRF error
        if form.errors.get("csrf_token"):
            return render_template(
                "_partials/test_result.html",
                status="error",
                message=_("Please refresh the page and try again (CSRF token expired)"),
            )
        return render_template(
            "_partials/test_result.html",
            status="error",
            message=_("Invalid form data: %(errors)s", errors=str(form.errors)),
        )

    # Create a temporary connection object for testing
    test_conn = Connection(
        connection_type=form.connection_type.data,
        name=form.name.data,
        url=form.url.data,
        api_key=form.api_key.data,
        media_server_id=form.media_server_id.data,
    )

    try:
        connection_type = form.connection_type.data
        if not connection_type:
            return render_template(
                "_partials/test_result.html",
                status="error",
                message=_("Connection type is required"),
            )

        client_class = get_companion_client(connection_type)
        client = client_class()
        result = client.test_connection(test_conn)

        return render_template(
            "_partials/test_result.html",
            status=result["status"],
            message=result["message"],
        )
    except ValueError:
        return render_template(
            "_partials/test_result.html",
            status="error",
            message=_("Unknown connection type"),
        )
