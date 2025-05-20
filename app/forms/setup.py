from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField
from wtforms.validators import DataRequired, EqualTo, Length, URL, Optional

class AdminAccountForm(FlaskForm):
    username = StringField(
        "Username",
        validators=[DataRequired(), Length(min=3, max=15)]
    )
    password = PasswordField(
        "Password",
        validators=[DataRequired(), Length(min=3, max=40)]
    )
    confirm = PasswordField(
        "Confirm password",
        validators=[DataRequired(), EqualTo("password", message="Passwords must match.")]
    )

class ServerVerificationForm(FlaskForm):
    server_name = StringField("Friendly name", validators=[DataRequired()])
    server_type = SelectField(
        "Platform", validators=[DataRequired()],
        choices=[("plex", "Plex"), ("jellyfin", "Jellyfin")]
    )
    server_url = StringField("Base URL", validators=[DataRequired(), URL()])
    api_key   = StringField("API Token", validators=[Optional()])
    libraries = StringField("Libraries (comma-separated)", validators=[DataRequired()])
    overseerr_url = StringField("Overseerr URL", validators=[Optional(), URL()])
    ombi_api_key  = StringField("Ombi API key", validators=[Optional()])
    discord_id    = StringField("Discord guild / channel ID", validators=[Optional()])
