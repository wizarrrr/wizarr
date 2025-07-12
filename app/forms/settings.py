# app/forms/settings.py
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, TextAreaField, BooleanField
from wtforms.validators import DataRequired, Optional, URL
from flask_babel import lazy_gettext as _l


class SettingsForm(FlaskForm):
    server_type   = SelectField(
        _l("Server Type"),
        choices=[("plex", "Plex"), ("jellyfin", "Jellyfin"), ("emby", "Emby"), ("audiobookshelf", "Audiobookshelf"), ("romm", "Romm"), ("komga", "Komga"), ("kavita", "Kavita")],
        validators=[DataRequired()],
    )
    server_name   = StringField(_l("Server Name"),   validators=[DataRequired()])
    server_url    = StringField(_l("Server URL"),    validators=[DataRequired()])
    api_key       = StringField(_l("API Key"),       validators=[Optional()])
    server_username = StringField(_l("RomM Username"), validators=[Optional()])
    server_password = StringField(_l("RomM Password"), validators=[Optional()])
    libraries     = StringField(_l("Libraries"),     validators=[Optional()])
    allow_downloads_plex = BooleanField(_l("Allow Downloads"), default=False, validators=[Optional()])
    allow_tv_plex = BooleanField(_l("Allow Live TV"), default=False, validators=[Optional()])
    overseerr_url = StringField(_l("Overseerr/Ombi URL"), validators=[Optional(), URL()])
    ombi_api_key  = StringField(_l("Ombi API Key"),  validators=[Optional()])
    discord_id    = StringField(_l("Discord ID"),    validators=[Optional()])
    external_url  = StringField(_l("External URL"), validators=[Optional()])
    
    # Jellyfin specific
    allow_downloads_jellyfin = BooleanField(_l("Allow Downloads"), default=False, validators=[Optional()])
    allow_tv_jellyfin       = BooleanField(_l("Allow Live TV"), default=False, validators=[Optional()])

    def __init__(self, install_mode: bool = False, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if install_mode:
            # During install wizard, libraries must be supplied
            self.libraries.validators = [DataRequired()]
            # api_key is mandatory for Plex/Jellyfin
            self.api_key.validators = [DataRequired()]
