from flask_babel import gettext as _
from flask_babel import lazy_gettext as _l
from flask_wtf import FlaskForm
from wtforms import BooleanField, Field, PasswordField, SelectField, StringField
from wtforms.validators import DataRequired, Optional, ValidationError

from app.forms.validators import strip_filter
from app.services.ldap.filters import is_valid_filter


def _valid_ldap_filter(_form: FlaskForm, field: Field) -> None:
    """Reject a filter that ldap3 cannot parse."""
    if field.data and not is_valid_filter(field.data):
        raise ValidationError(
            _(
                "This LDAP filter is not valid. Enter one complete filter in "
                "parentheses, for example %(example)s.",
                example="(memberOf=cn=users,ou=groups,dc=example,dc=com)",
            )
        )


class LDAPSettingsForm(FlaskForm):
    """Form for LDAP configuration settings."""

    # Connection settings
    enabled = BooleanField("Enable LDAP", default=False, validators=[Optional()])
    server_url = StringField(
        "LDAP Server URL",
        validators=[DataRequired()],
        render_kw={"placeholder": "ldap://ldap.example.com:389"},
    )
    use_tls = BooleanField("Use TLS", default=True, validators=[Optional()])
    verify_cert = BooleanField(
        "Verify Certificate", default=True, validators=[Optional()]
    )

    # Service account
    service_account_dn = StringField(
        "Service Account DN",
        validators=[Optional()],
        render_kw={"placeholder": "cn=wizarr,ou=people,dc=example,dc=com"},
    )
    service_account_password = PasswordField(
        "Service Account Password", validators=[Optional()]
    )

    # User settings
    user_base_dn = StringField(
        "User Base DN",
        validators=[DataRequired()],
        render_kw={"placeholder": "ou=people,dc=example,dc=com"},
    )
    user_search_filter = StringField(
        "User Search Filter",
        validators=[DataRequired()],
        default="(uid={username})",
        render_kw={"placeholder": "(uid={username})"},
    )
    username_attribute = StringField(
        "Username Attribute",
        validators=[DataRequired()],
        default="uid",
        render_kw={"placeholder": "uid"},
    )
    email_attribute = StringField(
        "Email Attribute",
        validators=[DataRequired()],
        default="mail",
        render_kw={"placeholder": "mail"},
    )

    user_object_class = StringField(
        "User Object Class",
        validators=[DataRequired()],
        default="inetOrgPerson",
        render_kw={"placeholder": "inetOrgPerson"},
    )
    user_sync_filter = StringField(
        str(_l("User Sync Filter")),
        filters=[strip_filter],
        validators=[Optional(), _valid_ldap_filter],
        render_kw={"placeholder": "(memberOf=cn=users,ou=groups,dc=example,dc=com)"},
    )

    # Group settings
    group_base_dn = StringField(
        "Group Base DN",
        validators=[Optional()],
        render_kw={"placeholder": "ou=groups,dc=example,dc=com"},
    )
    group_object_class = StringField(
        "Group Object Class",
        validators=[Optional()],
        default="groupOfUniqueNames",
        render_kw={"placeholder": "groupOfUniqueNames"},
    )
    group_member_attribute = StringField(
        "Group Member Attribute",
        validators=[Optional()],
        default="uniqueMember",
        render_kw={"placeholder": "uniqueMember"},
    )

    # Admin authentication
    allow_admin_bind = BooleanField(
        "Allow Admin Login via LDAP", default=False, validators=[Optional()]
    )
    admin_group_dn = SelectField(
        "Admin Group DN",
        choices=[],
        validators=[Optional()],
        coerce=lambda x: x or None,
    )
