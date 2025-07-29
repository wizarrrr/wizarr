from flask_wtf import FlaskForm
from wtforms import SelectField, StringField
from wtforms.validators import URL, DataRequired, Optional

from app.models import MediaServer


class ConnectionForm(FlaskForm):
    """Form for creating/editing connections."""

    connection_type = SelectField("Connection Type", validators=[DataRequired()])
    name = StringField("Connection Name", validators=[DataRequired()])
    url = StringField("Service URL", validators=[Optional(), URL()])
    api_key = StringField("API Key", validators=[Optional()])
    media_server_id = SelectField(
        "Media Server", coerce=int, validators=[DataRequired()]
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Connection type choices
        self.connection_type.choices = [
            ("ombi", "Ombi"),
            ("overseerr", "Overseerr/Jellyseerr (Info Only)"),
        ]

        # Populate media server choices
        self.media_server_id.choices = [
            (server.id, f"{server.name} ({server.server_type.title()})")
            for server in MediaServer.query.order_by(MediaServer.name).all()
        ]
