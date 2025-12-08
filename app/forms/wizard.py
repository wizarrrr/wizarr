"""Wizard step forms for admin configuration.

Forms for creating and editing wizard steps, including interaction
configuration support.
"""

from __future__ import annotations

import json
from typing import Any

from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField, FileRequired
from wtforms import BooleanField, HiddenField, SelectField, StringField, TextAreaField
from wtforms.validators import DataRequired, Optional, ValidationError

from app.interactions import StepInteractions


def validate_interaction_config(_form: FlaskForm, field: HiddenField) -> None:
    """Validate the interaction configuration JSON.

    Args:
        form: The parent form.
        field: The interaction_config field.

    Raises:
        ValidationError: If the JSON is invalid or interactions fail validation.
    """
    if not field.data or field.data == "{}":
        return

    try:
        data = json.loads(field.data)
    except json.JSONDecodeError as e:
        raise ValidationError(f"Invalid JSON: {e}") from e

    if not isinstance(data, dict):
        raise ValidationError("Interaction configuration must be a JSON object")

    # Validate using the StepInteractions dataclass
    interactions = StepInteractions.from_dict(data)
    errors = interactions.validate()
    if errors:
        raise ValidationError("; ".join(errors))


def parse_interaction_config(data: str | None) -> dict[str, Any] | None:
    """Parse interaction configuration JSON string.

    Args:
        data: JSON string or None.

    Returns:
        Parsed dict or None if empty/invalid.
    """
    if not data or data == "{}":
        return None

    try:
        parsed = json.loads(data)
        return parsed if isinstance(parsed, dict) and parsed else None
    except json.JSONDecodeError:
        return None


class WizardStepForm(FlaskForm):
    """Form for creating/editing wizard steps.

    The interaction_config field stores a JSON object with interaction
    configurations. The actual UI is rendered using Alpine.js in templates.
    """

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

    # JSON field storing all interaction configurations
    interaction_config = HiddenField(
        "Interaction Configuration",
        default="{}",
        validators=[validate_interaction_config],
    )

    def get_interactions(self) -> StepInteractions:
        """Get typed interaction configuration from form data.

        Returns:
            StepInteractions object with parsed configuration.
        """
        data = parse_interaction_config(self.interaction_config.data)
        return StepInteractions.from_dict(data)

    def set_interactions(
        self, interactions: StepInteractions | dict[str, Any] | None
    ) -> None:
        """Set interaction configuration on the form.

        Args:
            interactions: StepInteractions object, dict, or None.
        """
        if interactions is None:
            self.interaction_config.data = "{}"
        elif isinstance(interactions, StepInteractions):
            data = interactions.to_dict()
            self.interaction_config.data = json.dumps(data) if data else "{}"
        elif isinstance(interactions, dict):
            self.interaction_config.data = (
                json.dumps(interactions) if interactions else "{}"
            )
        else:
            self.interaction_config.data = "{}"


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


class SimpleWizardStepForm(FlaskForm):
    """Minimal form for bundle-only steps (no server_type, no requires).

    The interaction_config field stores a JSON object with interaction
    configurations, similar to WizardStepForm.
    """

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

    # JSON field storing all interaction configurations
    interaction_config = HiddenField(
        "Interaction Configuration",
        default="{}",
        validators=[validate_interaction_config],
    )

    def get_interactions(self) -> StepInteractions:
        """Get typed interaction configuration from form data.

        Returns:
            StepInteractions object with parsed configuration.
        """
        data = parse_interaction_config(self.interaction_config.data)
        return StepInteractions.from_dict(data)

    def set_interactions(
        self, interactions: StepInteractions | dict[str, Any] | None
    ) -> None:
        """Set interaction configuration on the form.

        Args:
            interactions: StepInteractions object, dict, or None.
        """
        if interactions is None:
            self.interaction_config.data = "{}"
        elif isinstance(interactions, StepInteractions):
            data = interactions.to_dict()
            self.interaction_config.data = json.dumps(data) if data else "{}"
        elif isinstance(interactions, dict):
            self.interaction_config.data = (
                json.dumps(interactions) if interactions else "{}"
            )
        else:
            self.interaction_config.data = "{}"


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
