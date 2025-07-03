# app/forms/settings.py
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, TextAreaField, BooleanField
from wtforms.validators import DataRequired, Optional, URL


class SettingsForm(FlaskForm):
    server_type   = SelectField(
        "Server Type",
        choices=[("plex", "Plex"), ("jellyfin", "Jellyfin"), ("emby", "Emby"), ("audiobookshelf", "Audiobookshelf"), ("romm", "Romm")],
        validators=[DataRequired()],
    )
    server_name   = StringField("Server Name",   validators=[DataRequired()])
    server_url    = StringField("Server URL",    validators=[DataRequired()])
    api_key       = StringField("API Key",       validators=[Optional()])
    server_username = StringField("RomM Username", validators=[Optional()])
    server_password = StringField("RomM Password", validators=[Optional()])
    libraries     = StringField("Libraries",     validators=[Optional()])
    allow_downloads_plex = BooleanField("Allow Downloads", default=False, validators=[Optional()])
    allow_tv_plex = BooleanField("Allow Live TV", default=False, validators=[Optional()])
    overseerr_url = StringField("Overseerr/Ombi URL", validators=[Optional(), URL()])
    ombi_api_key  = StringField("Ombi API Key",  validators=[Optional()])
    discord_id    = StringField("Discord ID",    validators=[Optional()])
    external_url  = StringField("External URL", validators=[Optional()])
    
    # Jellyfin specific
    allow_downloads_jellyfin = BooleanField("Allow Downloads", default=False, validators=[Optional()])
    allow_tv_jellyfin       = BooleanField("Allow Live TV", default=False, validators=[Optional()])

    def __init__(self, install_mode: bool = False, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if install_mode:
            # During install wizard, libraries must be supplied
            self.libraries.validators = [DataRequired()]
            # api_key is mandatory for Plex/Jellyfin
            self.api_key.validators = [DataRequired()]
