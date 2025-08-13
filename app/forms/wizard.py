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
            ("komga", "Komga"),
            ("kavita", "Kavita"),
        ],
        validators=[DataRequired()],
    )

    position = HiddenField("Position", default="0")

    title = StringField("Title", validators=[Optional()])

    markdown = TextAreaField("Markdown", validators=[DataRequired()])

    # Removed requires field as part of requires system overhaul


class WizardPresetForm(FlaskForm):
    """Form for creating wizard steps from presets."""

    server_type = SelectField(
        "Server Type",
        choices=[
            ("plex", "Plex"),
            ("jellyfin", "Jellyfin"),
            ("emby", "Emby"),
            ("audiobookshelf", "Audiobookshelf"),
            ("romm", "Romm"),
            ("komga", "Komga"),
            ("kavita", "Kavita"),
        ],
        validators=[DataRequired()],
    )

    preset_id = SelectField(
        "Preset",
        choices=[],  # Will be populated dynamically
        validators=[DataRequired()],
    )

    # Variables for preset templates
    discord_id = StringField("Discord Server ID", validators=[Optional()])
    overseerr_url = StringField("Overseerr/Ombi URL", validators=[Optional()])


class WizardBundleForm(FlaskForm):
    """Simple form to create / edit a WizardBundle."""

    name = StringField("Name", validators=[DataRequired()])
    description = StringField("Description", validators=[Optional()])
    # optional: Steps selection handled in separate UI; keep form minimal


class SimpleWizardStepForm(FlaskForm):
    """Minimal form for bundle-only steps (no server_type, no requires)."""

    title = StringField("Title", validators=[Optional()])
    markdown = TextAreaField("Markdown", validators=[DataRequired()])
