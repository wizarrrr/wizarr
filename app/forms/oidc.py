from flask_wtf import FlaskForm
from wtforms import BooleanField, PasswordField, StringField
from wtforms.validators import URL, DataRequired, Optional


class OIDCSettingsForm(FlaskForm):
    """Form for OIDC (admin-panel SSO) configuration settings."""

    enabled = BooleanField("Enable OIDC Sign-In", default=False, validators=[Optional()])

    display_name = StringField(
        "Provider Display Name",
        validators=[Optional()],
        default="SSO",
        render_kw={"placeholder": "Authentik"},
    )

    discovery_url = StringField(
        "Discovery URL",
        validators=[DataRequired(), URL(require_tld=False)],
        render_kw={
            "placeholder": "https://auth.example.com/application/o/wizarr/.well-known/openid-configuration"
        },
    )
    client_id = StringField("Client ID", validators=[DataRequired()])
    client_secret = PasswordField("Client Secret", validators=[Optional()])
    scopes = StringField(
        "Scopes",
        validators=[DataRequired()],
        default="openid profile email",
        render_kw={"placeholder": "openid profile email"},
    )

    username_claim = StringField(
        "Username Claim",
        validators=[DataRequired()],
        default="preferred_username",
        render_kw={"placeholder": "preferred_username"},
    )

    admin_claim = StringField(
        "Admin Claim",
        validators=[Optional()],
        render_kw={"placeholder": "groups"},
    )
    admin_claim_values = StringField(
        "Admin Claim Allowed Values",
        validators=[Optional()],
        render_kw={"placeholder": "wizarr-admins, admins"},
    )
