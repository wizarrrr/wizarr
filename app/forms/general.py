from flask_wtf import FlaskForm
from wtforms import BooleanField, SelectField, StringField
from wtforms.validators import URL, DataRequired, Optional


class GeneralSettingsForm(FlaskForm):
    server_name = StringField("Display Name", validators=[DataRequired()])
    public_url = StringField(
        "Public Wizarr URL",
        validators=[Optional(), URL(require_tld=False)],
        description=(
            "Overrides the auto-detected address used in invite and "
            "password-reset links, e.g. https://invites.example.com. "
            "Leave blank to keep using whatever URL the admin is browsing "
            "from (the previous behavior)."
        ),
    )
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
