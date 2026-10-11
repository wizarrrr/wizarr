"""Wizard step preset templates and management.

Provides hardcoded preset templates for common integrations like Discord and Overseerr,
allowing users to quickly add wizard steps through the Multi-Action create button.
"""

from dataclasses import dataclass

__all__ = ["WizardPreset", "create_step_from_preset", "get_available_presets"]


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
        template="""## 💬 Join Our Discord Community

Stay connected with other users, get help, and share tips in our Discord server!

|||
### 🎮 What is Discord?

Discord is a free chat platform where our community hangs out. Join us to:

- Get help from other users
- Share your experience
- Stay updated on new content
- Connect with fellow enthusiasts

<div class="flex justify-center my-4">
    <iframe src="https://discord.com/widget?id={discord_id}&theme=dark"
            width="350" height="500"
            allowtransparency="true" frameborder="0"
            sandbox="allow-popups allow-same-origin allow-scripts"
            class="rounded-lg shadow-lg"></iframe>
</div>
|||""",
    ),
    "overseerr_requests": WizardPreset(
        id="overseerr_requests",
        name="Overseerr/Ombi Requests",
        description="Add a link to your Overseerr/Ombi instance for media requests",
        title="Automatic requests",
        template="""## 🎬 Request New Content

Can't find what you're looking for? No problem!

|||
### 📝 Automatic Media Requests

Use our request system to ask for new movies or TV shows. Once approved, they'll be automatically downloaded and added to the library for everyone to enjoy.

**How it works:**
1. Search for the title you want
2. Submit your request
3. Get notified when it's available

|||

{{{{ widget:button url="{overseerr_url}" text="🎯 Open Request System" }}}}""",
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
