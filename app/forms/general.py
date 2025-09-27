from flask_wtf import FlaskForm
from wtforms import BooleanField, SelectField, StringField
from wtforms.validators import DataRequired, Optional


class GeneralSettingsForm(FlaskForm):
    server_name = StringField("Display Name", validators=[DataRequired()])
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
