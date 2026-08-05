from flask_wtf import FlaskForm
from wtforms import BooleanField, IntegerField, SelectField, StringField
from wtforms.validators import DataRequired, NumberRange, Optional


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
    password_reset_min_length = IntegerField(
        "Minimum Length",
        default=8,
        validators=[DataRequired(), NumberRange(min=8, max=128)],
    )
    password_reset_max_length = IntegerField(
        "Maximum Length",
        default=128,
        validators=[DataRequired(), NumberRange(min=8, max=128)],
    )
    password_reset_security_level = IntegerField(
        "Security Level",
        default=2,
        validators=[DataRequired(), NumberRange(min=0, max=4)],
    )

    def validate(self, extra_validators=None):
        if not super().validate(extra_validators=extra_validators):
            return False

        if (
            self.password_reset_min_length.data is not None
            and self.password_reset_max_length.data is not None
            and self.password_reset_max_length.data
            < self.password_reset_min_length.data
        ):
            self.password_reset_max_length.errors.append(
                "Maximum length must be greater than or equal to minimum length."
            )
            return False

        return True
