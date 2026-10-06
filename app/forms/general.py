from flask_babel import lazy_gettext as _l
from flask_wtf import FlaskForm
from wtforms import BooleanField, IntegerField, PasswordField, SelectField, StringField
from wtforms.validators import DataRequired, Email, NumberRange, Optional


class GeneralSettingsForm(FlaskForm):
    server_name = StringField(str(_l("Display Name")), validators=[DataRequired()])
    wizard_acl_enabled = BooleanField(
        str(_l("Protect Wizard Access")), default=True, validators=[Optional()]
    )
    expiry_action = SelectField(
        str(_l("Expiry Action")),
        choices=[
            ("delete", str(_l("Delete User"))),
            ("disable", str(_l("Disable User (if supported)"))),
        ],
        default="delete",
        validators=[DataRequired()],
    )


class MailingSettingsForm(FlaskForm):
    smtp_enabled = BooleanField(
        str(_l("Enable User Lifecycle Emails")), validators=[Optional()]
    )
    smtp_host = StringField(str(_l("SMTP Host")), validators=[Optional()])
    smtp_port = IntegerField(
        str(_l("SMTP Port")),
        validators=[Optional(), NumberRange(min=1, max=65535)],
        default=587,
    )
    smtp_username = StringField(str(_l("SMTP Username")), validators=[Optional()])
    smtp_password = PasswordField(str(_l("SMTP Password")), validators=[Optional()])
    smtp_from_address = StringField(
        str(_l("Sender Email Address")), validators=[Optional(), Email()]
    )
    smtp_from_name = StringField(str(_l("Sender Name")), validators=[Optional()])
    smtp_use_tls = BooleanField(
        str(_l("Use STARTTLS")), default=True, validators=[Optional()]
    )
    smtp_use_ssl = BooleanField(str(_l("Use SSL/TLS")), validators=[Optional()])
    smtp_language = SelectField(
        str(_l("Email Language")),
        choices=[("en", str(_l("English"))), ("de", str(_l("Deutsch")))],
        default="en",
        validators=[DataRequired()],
    )

    def validate(self, extra_validators=None):  # type: ignore[override]
        is_valid = super().validate(extra_validators=extra_validators)
        if not self.smtp_enabled.data:
            return is_valid

        required_fields = {
            "smtp_host": self.smtp_host,
            "smtp_port": self.smtp_port,
            "smtp_from_address": self.smtp_from_address,
        }
        for field in required_fields.values():
            if not field.data:
                field.errors.append(
                    str(_l("This field is required when SMTP emails are enabled."))
                )
                is_valid = False

        if self.smtp_use_tls.data and self.smtp_use_ssl.data:
            self.smtp_use_ssl.errors.append(
                str(_l("Choose either STARTTLS or SSL/TLS, not both."))
            )
            is_valid = False

        return is_valid
