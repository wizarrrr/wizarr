# app/forms/settings.py
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, TextAreaField, BooleanField
from wtforms.validators import DataRequired, Optional, URL


class SettingsForm(FlaskForm):
    server_type   = SelectField(
        "Server Type",
        choices=[("plex", "Plex"), ("jellyfin", "Jellyfin"), ("emby", "Emby")],
        validators=[DataRequired()],
    )
    server_name   = StringField("Server Name",   validators=[DataRequired()])
    server_url    = StringField("Server URL",    validators=[DataRequired()])
    api_key       = StringField("API Key",       validators=[Optional()])
    libraries     = StringField("Libraries",     validators=[Optional()])
    overseerr_url = StringField("Overseerr/Ombi URL", validators=[Optional(), URL()])
    ombi_api_key  = StringField("Ombi API Key",  validators=[Optional()])
    discord_id    = StringField("Discord ID",    validators=[Optional()])
    allow_downloads_plex = BooleanField("Allow Downloads", default=False)

    def __init__(self, install_mode: bool = False, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if install_mode:
            # During install wizard, libraries must be supplied
            self.libraries.validators = [DataRequired()]
            # api_key is mandatory for Plex/Jellyfin
            self.api_key.validators = [DataRequired()]

    def validate(self):
        if not super().validate():
            return False

        # If server type is not Plex, ensure Plex-specific settings are False
        if self.server_type.data != "plex":
            self.allow_downloads_plex.data = False

        return True
