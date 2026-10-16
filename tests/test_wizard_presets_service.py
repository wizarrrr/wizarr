"""Tests for wizard presets service.

Tests the wizard_presets service which provides preset templates for common
integrations like Discord and Overseerr.
"""

import pytest

from app.services.wizard_presets import create_step_from_preset, get_preset_title

# ─── Test create_step_from_preset() ───────────────────────────────────


def test_create_step_from_preset_discord():
    """Test creating a step from discord_community preset."""
    discord_id = "123456789"
    content = create_step_from_preset("discord_community", discord_id=discord_id)

    assert discord_id in content
    assert "{discord_id}" not in content  # Template variable should be replaced
    assert "discord" in content.lower()


def test_create_step_from_preset_overseerr():
    """Test creating a step from overseerr_requests preset."""
    overseerr_url = "https://overseerr.example.com"
    content = create_step_from_preset("overseerr_requests", overseerr_url=overseerr_url)

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


# ─── Test get_preset_title() ──────────────────────────────────────────


def test_get_preset_title_invalid_preset_id():
    """Test that getting title with invalid preset ID raises KeyError."""
    with pytest.raises(KeyError) as exc_info:
        get_preset_title("nonexistent_preset")

    assert "not found" in str(exc_info.value).lower()
