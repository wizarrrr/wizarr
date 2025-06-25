from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, HiddenField
from wtforms.validators import DataRequired, Optional


class WizardStepForm(FlaskForm):
    server_type = SelectField(
        "Server Type",
        choices=[
            ("plex", "Plex"),
            ("jellyfin", "Jellyfin"),
            ("emby", "Emby"),
            ("audiobookshelf", "Audiobookshelf"),
            ("romm", "Romm"),
        ],
        validators=[DataRequired()],
    )

    position = HiddenField("Position", default="0")

    title = StringField("Title", validators=[Optional()])

    markdown = TextAreaField("Markdown", validators=[DataRequired()])

    requires = StringField(
        "Requires (comma-separated setting keys)", validators=[Optional()]
    ) 