from flask_wtf import FlaskForm
from wtforms import BooleanField, SelectField, StringField
from wtforms.validators import DataRequired, Optional


class GeneralSettingsForm(FlaskForm):
    server_name = StringField("Display Name", validators=[DataRequired()])
    wizard_acl_enabled = BooleanField(
        "Protect Wizard Access", default=True, validators=[Optional()]
    )
    expiry_action = SelectField(
        "Expiry Action",
        choices=[
            ("delete", "Delete User"),
            ("disable", "Disable User (if supported)"),
        ],
        default="delete",
        validators=[DataRequired()],
    )
    cinema_posters_source = SelectField(
        "Join Page Posters",
        choices=[],
        default="",
        validators=[Optional()],
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from app.models import MediaServer

        self.cinema_posters_source.choices = [
            ("", "First server (default)"),
            ("invite", "The server the invite is for"),
        ] + [
            (str(server.id), server.name)
            for server in MediaServer.query.order_by(MediaServer.name).all()
        ]
