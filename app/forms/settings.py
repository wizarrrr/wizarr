# app/forms/settings.py
from flask_babel import lazy_gettext as _l
from flask_wtf import FlaskForm
from wtforms import BooleanField, SelectField, StringField
from wtforms.validators import URL, DataRequired, Optional


class SettingsForm(FlaskForm):
    server_type = SelectField(
        str(_l("Server Type")),
        choices=[
            ("plex", "Plex"),
            ("jellyfin", "Jellyfin"),
            ("emby", "Emby"),
            ("audiobookshelf", "Audiobookshelf"),
            ("romm", "Romm"),
            ("komga", "Komga"),
            ("kavita", "Kavita"),
            ("navidrome", "Navidrome"),
        ],
        validators=[DataRequired()],
    )
    server_name = StringField(str(_l("Server Name")), validators=[DataRequired()])
    server_url = StringField(str(_l("Server URL")), validators=[DataRequired()])
    api_key = StringField(str(_l("API Key")), validators=[Optional()])
    server_username = StringField(str(_l("RomM Username")), validators=[Optional()])
    server_password = StringField(str(_l("RomM Password")), validators=[Optional()])
    libraries = StringField(str(_l("Libraries")), validators=[Optional()])
    allow_downloads = BooleanField(
        str(_l("Allow Downloads")), default=False, validators=[Optional()]
    )
    allow_live_tv = BooleanField(
        str(_l("Allow Live TV")), default=False, validators=[Optional()]
    )
    overseerr_url = StringField(
        str(_l("Overseerr/Ombi URL")), validators=[Optional(), URL()]
    )
    ombi_api_key = StringField(str(_l("Ombi API Key")), validators=[Optional()])
    discord_id = StringField(str(_l("Discord ID")), validators=[Optional()])
    external_url = StringField(str(_l("External URL")), validators=[Optional()])

    # Universal download and live TV options (no longer server-specific)

    # Audiobookshelf specific
    allow_downloads_audiobookshelf = BooleanField(
        str(_l("Allow Downloads")), default=True, validators=[Optional()]
    )

    def __init__(self, install_mode: bool = False, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if install_mode:
            # During install wizard, libraries must be supplied
            self.libraries.validators = [DataRequired()]
            # api_key is mandatory for Plex/Jellyfin
            self.api_key.validators = [DataRequired()]
