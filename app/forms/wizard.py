from flask_babel import lazy_gettext as _l
from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField, FileRequired
from wtforms import (
    BooleanField,
    HiddenField,
    IntegerField,
    PasswordField,
    SelectField,
    StringField,
    TextAreaField,
)
from wtforms.validators import DataRequired, Optional


class ApiCheckFieldsMixin:
    """Fields for the wizard API-check gate.

    Deliberately loose validators – ``Optional()`` everywhere, no range or
    URL checks. ``app.services.wizard_api_check.config.from_form`` is where
    submitted values are actually judged, so a rejected value is echoed back
    for the admin to fix rather than clamped here without them noticing.
    """

    api_check_enabled = BooleanField(
        str(_l("Enable API Gate")),
        default=False,
        description=str(
            _l(
                "Block this step until an external API confirms the invited "
                "user. Only takes effect on post-invite steps, since that is "
                "the earliest point a username and email exist to check."
            )
        ),
    )

    api_check_method = SelectField(
        str(_l("Method")),
        choices=[("GET", "GET"), ("POST", "POST")],
        default="GET",
        description=str(_l("HTTP method used to call the endpoint.")),
    )

    api_check_url = StringField(
        str(_l("Endpoint URL")),
        validators=[Optional()],
        description=str(
            _l(
                "The API to call, e.g. https://example.com/check. Must be a "
                "plain http(s) URL with no embedded credentials."
            )
        ),
    )

    api_check_auth_header = StringField(
        str(_l("Auth Header")),
        validators=[Optional()],
        description=str(_l("Header the API key is sent under, e.g. Authorization.")),
    )

    api_check_auth_prefix = StringField(
        str(_l("Auth Prefix")),
        validators=[Optional()],
        description=str(
            _l('Text placed before the key in that header, e.g. "Bearer ".')
        ),
    )

    api_check_api_key = PasswordField(
        str(_l("API Key")),
        validators=[Optional()],
        description=str(
            _l(
                "Sent in the auth header above. Leave blank to keep the "
                "currently stored key – it is never shown here once saved."
            )
        ),
    )

    api_check_clear_key = BooleanField(
        str(_l("Remove stored key")),
        default=False,
        description=str(
            _l(
                "Delete the saved key instead of keeping it. A signed gate "
                "left without a key stays inactive rather than blocking users."
            )
        ),
    )

    api_check_code_param = StringField(
        str(_l("Code Parameter")),
        validators=[Optional()],
        description=str(
            _l("The invite code is sent to the endpoint under this parameter name.")
        ),
    )

    api_check_username_param = StringField(
        str(_l("Username Parameter")),
        validators=[Optional()],
        description=str(
            _l("The invited user's username is sent under this parameter name.")
        ),
    )

    api_check_email_param = StringField(
        str(_l("Email Parameter")),
        validators=[Optional()],
        description=str(
            _l("The invited user's email is sent under this parameter name.")
        ),
    )

    api_check_expect_status = StringField(
        str(_l("Expected Status Codes")),
        validators=[Optional()],
        description=str(
            _l(
                'Comma-separated HTTP status codes that count as a pass, e.g. "200, 204".'
            )
        ),
    )

    api_check_interval_seconds = IntegerField(
        str(_l("Poll Interval (seconds)")),
        validators=[Optional()],
        description=str(
            _l("How often the browser re-checks while waiting (5-300 seconds).")
        ),
    )

    api_check_timeout_seconds = IntegerField(
        str(_l("Request Timeout (seconds)")),
        validators=[Optional()],
        description=str(
            _l(
                "How long to wait for the endpoint to respond before counting "
                "the attempt as failed (1-15 seconds)."
            )
        ),
    )

    api_check_max_poll_seconds = IntegerField(
        str(_l("Give Up After (seconds)")),
        validators=[Optional()],
        description=str(
            _l(
                "Stop auto-polling after this long (30-3600 seconds); the "
                "user can still tap Re-check by hand."
            )
        ),
    )

    api_check_sign_requests = BooleanField(
        str(_l("Sign Requests")),
        default=True,
        description=str(
            _l(
                "Sign each request with an HMAC of the key above, a "
                "timestamp and a nonce. Your endpoint should reject "
                "timestamps more than 300 seconds old and track nonces to "
                "stop replayed requests."
            )
        ),
    )

    api_check_pending_message = TextAreaField(
        str(_l("Pending Message")),
        validators=[Optional()],
        description=str(
            _l(
                "Shown while waiting for a passing check. Plain text only – "
                "template syntax is rejected."
            )
        ),
    )

    api_check_success_message = TextAreaField(
        str(_l("Success Message")),
        validators=[Optional()],
        description=str(
            _l(
                "Shown once the check passes. Plain text only – template "
                "syntax is rejected."
            )
        ),
    )


class WizardStepForm(ApiCheckFieldsMixin, FlaskForm):
    server_type = SelectField(
        "Server Type",
        choices=[
            ("plex", "Plex"),
            ("jellyfin", "Jellyfin"),
            ("emby", "Emby"),
            ("audiobookshelf", "Audiobookshelf"),
            ("romm", "Romm"),
            ("komga", "Komga"),
            ("kavita", "Kavita"),
        ],
        validators=[DataRequired()],
    )

    category = SelectField(
        "Category",
        choices=[
            ("pre_invite", "Before Invite Acceptance"),
            ("post_invite", "After Invite Acceptance"),
        ],
        default="post_invite",
        validators=[DataRequired()],
    )

    position = HiddenField("Position", default="0")

    title = StringField("Title", validators=[Optional()])

    markdown = TextAreaField("Markdown", validators=[DataRequired()])

    # Require explicit user interaction before enabling Next
    require_interaction = BooleanField(
        "Require User Interaction",
        default=False,
        description="Block the user continuing, until they click a button or link in this step.",
    )


class WizardPresetForm(FlaskForm):
    """Form for creating wizard steps from presets."""

    server_type = SelectField(
        "Server Type",
        choices=[
            ("plex", "Plex"),
            ("jellyfin", "Jellyfin"),
            ("emby", "Emby"),
            ("audiobookshelf", "Audiobookshelf"),
            ("romm", "Romm"),
            ("komga", "Komga"),
            ("kavita", "Kavita"),
        ],
        validators=[DataRequired()],
    )

    category = SelectField(
        "Category",
        choices=[
            ("pre_invite", "Before Invite Acceptance"),
            ("post_invite", "After Invite Acceptance"),
        ],
        default="post_invite",
        validators=[DataRequired()],
    )

    preset_id = SelectField(
        "Preset",
        choices=[],  # Will be populated dynamically
        validators=[DataRequired()],
    )

    # Variables for preset templates
    discord_id = StringField("Discord Server ID", validators=[Optional()])
    overseerr_url = StringField("Overseerr/Ombi URL", validators=[Optional()])


class WizardBundleForm(FlaskForm):
    """Simple form to create / edit a WizardBundle."""

    name = StringField("Name", validators=[DataRequired()])
    description = StringField("Description", validators=[Optional()])
    # optional: Steps selection handled in separate UI; keep form minimal


class SimpleWizardStepForm(ApiCheckFieldsMixin, FlaskForm):
    """Minimal form for bundle-only steps (no server_type, no requires)."""

    category = SelectField(
        "Category",
        choices=[
            ("pre_invite", "Before Invite Acceptance"),
            ("post_invite", "After Invite Acceptance"),
        ],
        default="post_invite",
        validators=[DataRequired()],
    )

    title = StringField("Title", validators=[Optional()])
    markdown = TextAreaField("Markdown", validators=[DataRequired()])

    # Allow interaction requirement for custom/bundle steps as well
    require_interaction = BooleanField(
        "Require User Interaction",
        default=False,
        description="Block the user continuing, until they click a button or link in this step.",
    )


class WizardImportForm(FlaskForm):
    """Form for importing wizard steps or bundles from JSON files."""

    file = FileField(
        "JSON File",
        validators=[
            FileRequired("Please select a JSON file to import."),
            FileAllowed(["json"], "Only JSON files are allowed."),
        ],
    )

    replace_existing = BooleanField(
        "Replace Existing",
        default=False,
        description="Check to replace existing data, leave unchecked to merge with existing.",
    )
