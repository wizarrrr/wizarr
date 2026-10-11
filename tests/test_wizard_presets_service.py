"""Tests for wizard presets service.

Tests the wizard_presets service which provides preset templates for common
integrations like Discord and Overseerr.
"""

import pytest

from app.extensions import db
from app.services.wizard_presets import (
    PRESETS,
    WizardPreset,
    create_step_from_preset,
    get_available_presets,
    get_preset_title,
)


@pytest.fixture
def session(app):
    """Return a clean database session inside an app context."""
    from app.models import WizardStep

    with app.app_context():
        # Clean up any existing WizardStep data before the test
        db.session.query(WizardStep).delete()
        db.session.commit()

        yield db.session

        # Clean up after the test
        db.session.rollback()


# ─── Test Preset Data Structure ───────────────────────────────────────


def test_presets_are_defined():
    """Test that presets dictionary is not empty."""
    assert len(PRESETS) > 0
    assert isinstance(PRESETS, dict)


def test_preset_structure():
    """Test that each preset has the required structure."""
    for preset_id, preset in PRESETS.items():
        assert isinstance(preset, WizardPreset)
        assert preset.id == preset_id
        assert isinstance(preset.name, str)
        assert len(preset.name) > 0
        assert isinstance(preset.description, str)
        assert len(preset.description) > 0
        assert isinstance(preset.template, str)
        assert len(preset.template) > 0
        assert isinstance(preset.title, str)
        assert len(preset.title) > 0


def test_discord_community_preset_exists():
    """Test that discord_community preset is available."""
    assert "discord_community" in PRESETS
    preset = PRESETS["discord_community"]
    assert preset.name == "Discord Community"
    assert "discord" in preset.description.lower()
    assert "{discord_id}" in preset.template


def test_overseerr_requests_preset_exists():
    """Test that overseerr_requests preset is available."""
    assert "overseerr_requests" in PRESETS
    preset = PRESETS["overseerr_requests"]
    assert preset.name == "Overseerr/Ombi Requests"
    assert (
        "overseerr" in preset.description.lower()
        or "ombi" in preset.description.lower()
    )
    assert "{overseerr_url}" in preset.template


# ─── Test get_available_presets() ─────────────────────────────────────


def test_get_available_presets_returns_list():
    """Test that get_available_presets returns a list."""
    presets = get_available_presets()
    assert isinstance(presets, list)
    assert len(presets) > 0


def test_get_available_presets_returns_wizard_presets():
    """Test that get_available_presets returns WizardPreset objects."""
    presets = get_available_presets()
    for preset in presets:
        assert isinstance(preset, WizardPreset)


def test_get_available_presets_matches_presets_dict():
    """Test that get_available_presets returns all presets from PRESETS."""
    presets = get_available_presets()
    assert len(presets) == len(PRESETS)
    preset_ids = {p.id for p in presets}
    assert preset_ids == set(PRESETS.keys())


# ─── Test create_step_from_preset() ───────────────────────────────────


def test_create_step_from_preset_discord():
    """Test creating a step from discord_community preset."""
    discord_id = "123456789"
    content = create_step_from_preset("discord_community", discord_id=discord_id)

    assert isinstance(content, str)
    assert len(content) > 0
    assert discord_id in content
    assert "{discord_id}" not in content  # Template variable should be replaced
    assert "discord" in content.lower()


def test_create_step_from_preset_overseerr():
    """Test creating a step from overseerr_requests preset."""
    overseerr_url = "https://overseerr.example.com"
    content = create_step_from_preset("overseerr_requests", overseerr_url=overseerr_url)

    assert isinstance(content, str)
    assert len(content) > 0
    assert overseerr_url in content
    assert "{overseerr_url}" not in content  # Template variable should be replaced
    assert "request" in content.lower()


def test_create_step_from_preset_invalid_preset_id():
    """Test that creating a step with invalid preset ID raises KeyError."""
    with pytest.raises(KeyError) as exc_info:
        create_step_from_preset("nonexistent_preset")

    assert "not found" in str(exc_info.value).lower()


def test_create_step_from_preset_missing_required_variable():
    """Test that missing required template variables raises KeyError."""
    with pytest.raises(KeyError) as exc_info:
        create_step_from_preset("discord_community")  # Missing discord_id

    assert "discord_id" in str(exc_info.value).lower()


def test_create_step_from_preset_with_extra_variables():
    """Test that extra variables don't cause errors."""
    content = create_step_from_preset(
        "discord_community", discord_id="123456789", extra_var="should_be_ignored"
    )

    assert isinstance(content, str)
    assert "123456789" in content


# ─── Test get_preset_title() ──────────────────────────────────────────


def test_get_preset_title_discord():
    """Test getting title for discord_community preset."""
    title = get_preset_title("discord_community")
    assert isinstance(title, str)
    assert len(title) > 0
    assert title == "Discord community"


def test_get_preset_title_overseerr():
    """Test getting title for overseerr_requests preset."""
    title = get_preset_title("overseerr_requests")
    assert isinstance(title, str)
    assert len(title) > 0
    assert title == "Automatic requests"


def test_get_preset_title_invalid_preset_id():
    """Test that getting title with invalid preset ID raises KeyError."""
    with pytest.raises(KeyError) as exc_info:
        get_preset_title("nonexistent_preset")

    assert "not found" in str(exc_info.value).lower()


# ─── Test Preset Template Content ─────────────────────────────────────


def test_discord_preset_template_has_iframe():
    """Test that discord preset template includes iframe widget."""
    preset = PRESETS["discord_community"]
    assert "<iframe" in preset.template
    assert "discord.com/widget" in preset.template


def test_overseerr_preset_template_has_button_widget():
    """Test that overseerr preset template includes button widget."""
    preset = PRESETS["overseerr_requests"]
    assert "widget:button" in preset.template


def test_preset_templates_use_markdown():
    """Test that preset templates use markdown formatting."""
    for preset in PRESETS.values():
        # Check for common markdown elements
        has_markdown = (
            "##" in preset.template  # Headers
            or "**" in preset.template  # Bold
            or "|||" in preset.template  # Columns
            or "{{{{" in preset.template  # Widgets
        )
        assert has_markdown, f"Preset {preset.id} should use markdown formatting"


# ─── Test Category Independence ───────────────────────────────────────


def test_presets_are_category_agnostic():
    """Test that presets don't specify category (category is set by form)."""
    for preset in PRESETS.values():
        # Presets should not have a category field
        assert not hasattr(preset, "category")
        # Category should not be mentioned in template
        assert "category" not in preset.template.lower()


def test_preset_can_be_used_for_any_category():
    """Test that the same preset can be used for both pre and post-invite steps."""
    # This is a conceptual test - presets are category-agnostic
    # The category is determined by the form when creating the step
    discord_id = "123456789"

    # Create content from preset (same for both categories)
    content = create_step_from_preset("discord_community", discord_id=discord_id)

    # Content should be identical regardless of intended category
    assert isinstance(content, str)
    assert discord_id in content

    # The preset service doesn't care about category - that's handled by the route


# ─── Test Integration with WizardStep Model ───────────────────────────


def test_preset_content_can_be_used_for_both_categories(session):
    """Test that preset content can be used for both pre and post-invite steps.

    This demonstrates that presets are category-agnostic - the same preset
    content can be used for steps in either category.
    """
    from app.models import WizardStep

    # Create content from preset
    content = create_step_from_preset("discord_community", discord_id="123456789")
    title = get_preset_title("discord_community")

    # Create wizard step with pre_invite category
    step_pre = WizardStep(
        server_type="plex",
        category="pre_invite",
        position=0,
        title=title,
        markdown=content,
    )
    session.add(step_pre)
    session.commit()

    # Verify pre-invite step was created
    assert step_pre.id is not None
    assert step_pre.category == "pre_invite"

    # Create wizard step with post_invite category (same content, different category)
    step_post = WizardStep(
        server_type="plex",
        category="post_invite",
        position=0,  # Same position is OK because different category
        title=title,
        markdown=content,
    )
    session.add(step_post)
    session.commit()

    # Verify post-invite step was created
    assert step_post.id is not None
    assert step_post.category == "post_invite"

    # Verify both steps have the same content but different categories
    assert step_pre.markdown == step_post.markdown
    assert step_pre.category != step_post.category
