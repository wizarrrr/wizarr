from flask_wtf import FlaskForm
from wtforms import BooleanField, StringField
from wtforms.validators import DataRequired, Optional


class GeneralSettingsForm(FlaskForm):
    server_name = StringField("Display Name", validators=[DataRequired()])
    wizard_acl_enabled = BooleanField(
        "Protect Wizard Access", default=True, validators=[Optional()]
    )
