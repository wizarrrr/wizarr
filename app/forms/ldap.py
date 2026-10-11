from flask_wtf import FlaskForm
from wtforms import BooleanField, PasswordField, SelectField, StringField
from wtforms.validators import DataRequired, Optional


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
