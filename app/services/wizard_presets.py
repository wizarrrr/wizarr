"""Wizard step preset templates and management.

Provides hardcoded preset templates for common integrations like Discord and Overseerr,
allowing users to quickly add wizard steps through the Multi-Action create button.
"""

from dataclasses import dataclass

__all__ = ["WizardPreset", "get_available_presets", "create_step_from_preset"]


@dataclass
class WizardPreset:
    """Represents a wizard step preset template."""

    id: str
    name: str
    description: str
    template: str
    title: str


# Available preset templates
PRESETS = {
    "discord_community": WizardPreset(
        id="discord_community",
        name="Discord Community",
        description="Add a Discord server widget to invite users to your community",
        title="Discord community",
        template="""<iframe src="https://discord.com/widget?id={discord_id}&theme=dark"
        width="350" height="500"
        allowtransparency="true" frameborder="0"
        sandbox="allow-popups allow-same-origin allow-scripts"></iframe>""",
    ),
    "overseerr_requests": WizardPreset(
        id="overseerr_requests",
        name="Overseerr/Ombi Requests",
        description="Add a link to your Overseerr/Ombi instance for media requests",
        title="Automatic requests",
        template="""### {{ _("Automatic media requests") }}

{{ _("Can't find a title? Use our request system — it'll grab the film or episode automatically and add it to the library.") }}

[{{ _("Open Requests") }}]({overseerr_url}){{:target=_blank .btn}}""",
    ),
}


def get_available_presets() -> list[WizardPreset]:
    """Get list of all available preset templates."""
    return list(PRESETS.values())


def create_step_from_preset(preset_id: str, **kwargs) -> str:
    """Create wizard step content from a preset template.

    Args:
        preset_id: ID of the preset to use
        **kwargs: Variables to substitute in the template (e.g., discord_id, overseerr_url)

    Returns:
        Rendered template content with variables substituted

    Raises:
        KeyError: If preset_id is not found
        KeyError: If required template variables are missing
    """
    if preset_id not in PRESETS:
        raise KeyError(f"Preset '{preset_id}' not found")

    preset = PRESETS[preset_id]

    try:
        return preset.template.format(**kwargs)
    except KeyError as e:
        raise KeyError(
            f"Missing required variable for preset '{preset_id}': {e}"
        ) from e


def get_preset_title(preset_id: str) -> str:
    """Get the default title for a preset."""
    if preset_id not in PRESETS:
        raise KeyError(f"Preset '{preset_id}' not found")

    return PRESETS[preset_id].title
