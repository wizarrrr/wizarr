from flask_wtf import FlaskForm
from wtforms import BooleanField, SelectField, StringField
from wtforms.validators import URL, DataRequired, Optional

from app.models import MediaServer
from app.services.companions import list_companion_types


class ConnectionForm(FlaskForm):
    """Form for creating/editing connections."""

    connection_type = SelectField("Connection Type", validators=[DataRequired()])
    name = StringField("Connection Name", validators=[DataRequired()])
    url = StringField("Service URL", validators=[Optional(), URL()])
    api_key = StringField("API Key", validators=[Optional()])
    media_server_id = SelectField(
        "Media Server", coerce=int, validators=[DataRequired()]
    )
    provision_plex_users = BooleanField(
        "Create accounts for invited Plex users",
        description=(
            "Sign invited users in to this service during the Plex invite, so "
            "they do not have to visit it and log in themselves. Requires a "
            "Service URL."
        ),
        default=False,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Connection type choices - dynamically generated from registered companion clients
        self.connection_type.choices = list_companion_types()

        # Populate media server choices
        self.media_server_id.choices = [
            (server.id, f"{server.name} ({server.server_type.title()})")
            for server in MediaServer.query.order_by(MediaServer.name).all()
        ]
