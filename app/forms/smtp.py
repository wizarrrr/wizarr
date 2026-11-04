from flask_babel import lazy_gettext as _l
from flask_wtf import FlaskForm
from wtforms import BooleanField, IntegerField, PasswordField, SelectField, StringField
from wtforms.validators import DataRequired, Email, NumberRange, Optional


class SMTPSettingsForm(FlaskForm):
    """Form for SMTP configuration settings."""

    enabled = BooleanField(_l("Enable SMTP"), default=False, validators=[Optional()])

    host = StringField(
        _l("SMTP Host"),
        validators=[DataRequired()],
        render_kw={"placeholder": "smtp.example.com"},
    )
    port = IntegerField(
        _l("Port"),
        default=587,
        validators=[DataRequired(), NumberRange(min=1, max=65535)],
    )
    encryption = SelectField(
        _l("Encryption"),
        choices=[
            ("none", _l("None")),
            ("starttls", _l("STARTTLS")),
            ("ssl", _l("SSL/TLS")),
        ],
        default="starttls",
        validators=[DataRequired()],
    )

    username = StringField(_l("Username"), validators=[Optional()])
    password = PasswordField(_l("Password"), validators=[Optional()])

    from_email = StringField(
        _l("From Email"),
        validators=[DataRequired(), Email()],
        render_kw={"placeholder": "wizarr@example.com"},
    )
    from_name = StringField(_l("From Name"), validators=[Optional()], default="Wizarr")

    reminder_days_before = IntegerField(
        _l("Send expiry reminder (days before expiry)"),
        default=3,
        validators=[DataRequired(), NumberRange(min=0, max=90)],
    )


class SMTPTestEmailForm(FlaskForm):
    """Separate form for the 'send test email' button recipient field."""

    test_recipient_email = StringField(
        _l("Send test to"), validators=[DataRequired(), Email()]
    )
