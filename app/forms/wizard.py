from flask_wtf import FlaskForm
from wtforms import HiddenField, SelectField, StringField, TextAreaField
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


class WizardBundleForm(FlaskForm):
    """Simple form to create / edit a WizardBundle."""

    name = StringField("Name", validators=[DataRequired()])
    description = StringField("Description", validators=[Optional()])
    # optional: Steps selection handled in separate UI; keep form minimal


class SimpleWizardStepForm(FlaskForm):
    """Minimal form for bundle-only steps (no server_type, no requires)."""

    title = StringField("Title", validators=[Optional()])
    markdown = TextAreaField("Markdown", validators=[DataRequired()])
