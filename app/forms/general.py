from flask_wtf import FlaskForm
from wtforms import BooleanField, StringField
from wtforms.validators import URL, DataRequired, Optional


class GeneralSettingsForm(FlaskForm):
    server_name = StringField("Display Name", validators=[DataRequired()])
    overseerr_url = StringField("Overseerr/Ombi URL", validators=[Optional(), URL()])
    ombi_api_key = StringField("Ombi API Key", validators=[Optional()])
    discord_id = StringField("Discord Server ID", validators=[Optional()])
    wizard_acl_enabled = BooleanField(
        "Protect Wizard Access", default=True, validators=[Optional()]
    )
