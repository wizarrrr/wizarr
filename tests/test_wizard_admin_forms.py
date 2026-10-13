"""Tests for wizard admin form handling with category field."""

import re

import pytest

from app.extensions import db
from app.models import MediaServer, WizardStep


@pytest.fixture
def plex_server(session):
    """Create a Plex media server for testing."""
    server = MediaServer(
        name="Test Plex",
        server_type="plex",
        url="http://plex.test",
        api_key="test_key",
    )
    session.add(server)
    session.commit()
    return server


# ─── Test Category Field Validation ───────────────────────────────────


@pytest.mark.parametrize("category", ["pre_invite", "post_invite"])
def test_create_step_with_category(admin_client, plex_server, category):
    response = admin_client.post(
        "/settings/wizard/create",
        data={
            "server_type": "plex",
            "category": category,
            "title": "New Step",
            "markdown": "# New Step",
            "require_interaction": False,
        },
        follow_redirects=False,
    )

    assert response.status_code == 302
    step = WizardStep.query.filter_by(title="New Step").one()
    assert (step.server_type, step.category) == ("plex", category)


def test_create_step_default_category(admin_client, plex_server):
    """Test that category defaults to post_invite when not specified."""
    response = admin_client.post(
        "/settings/wizard/create",
        data={
            "server_type": "plex",
            "title": "Default Category Step",
            "markdown": "# Default\nShould default to post_invite",
            "require_interaction": False,
        },
        follow_redirects=False,
    )

    assert response.status_code == 302

    step = WizardStep.query.filter_by(server_type="plex").first()
    assert step is not None
    assert step.category == "post_invite"


def test_create_step_invalid_category_rejected(admin_client, plex_server):
    """Test that invalid category values are rejected by form validation."""
    response = admin_client.post(
        "/settings/wizard/create",
        data={
            "server_type": "plex",
            "category": "invalid_category",
            "title": "Invalid Category",
            "markdown": "# Test",
            "require_interaction": False,
        },
        follow_redirects=False,
    )

    # Should fail validation and return form with errors
    assert response.status_code == 200  # Returns form with errors

    # No step should be created
    step = WizardStep.query.filter_by(title="Invalid Category").first()
    assert step is None


# ─── Test Editing Step Category ───────────────────────────────────────


@pytest.mark.parametrize(
    ("old_category", "new_category"),
    [
        ("post_invite", "pre_invite"),
        ("pre_invite", "post_invite"),
        ("pre_invite", "pre_invite"),
    ],
    ids=["post-to-pre", "pre-to-post", "unchanged"],
)
def test_edit_step_category(
    admin_client, session, plex_server, old_category, new_category
):
    step = WizardStep(
        server_type="plex",
        category=old_category,
        position=0,
        title="Original Title",
        markdown="# Original",
    )
    session.add(step)
    session.commit()
    step_id = step.id

    response = admin_client.post(
        f"/settings/wizard/{step_id}/edit",
        data={
            "server_type": "plex",
            "category": new_category,
            "title": "Updated Title",
            "markdown": "# Updated",
            "require_interaction": False,
        },
        follow_redirects=False,
    )

    assert response.status_code == 302
    session.expire_all()
    updated_step = db.session.get(WizardStep, step_id)
    assert updated_step is not None
    assert updated_step.category == new_category
    assert updated_step.title == "Updated Title"


# ─── Test Preset Creation with Category ───────────────────────────────


@pytest.mark.parametrize(
    ("preset_id", "category", "fields", "title", "marker"),
    [
        (
            "discord_community",
            "pre_invite",
            {"discord_id": "123456789"},
            "Discord community",
            "discord",
        ),
        (
            "overseerr_requests",
            "post_invite",
            {"overseerr_url": "https://overseerr.example.com"},
            "Automatic requests",
            "overseerr",
        ),
    ],
)
def test_create_preset_with_category(
    admin_client, plex_server, preset_id, category, fields, title, marker
):
    response = admin_client.post(
        "/settings/wizard/create-preset",
        data={
            "preset_id": preset_id,
            "server_type": "plex",
            "category": category,
            **fields,
        },
        follow_redirects=False,
    )

    assert response.status_code == 302
    step = WizardStep.query.filter_by(
        server_type="plex", category=category, title=title
    ).first()
    assert step is not None
    assert marker in step.markdown.lower()


# ─── Test Simple Form (Bundle Steps) with Category ────────────────────


@pytest.mark.parametrize("category", ["pre_invite", "post_invite"])
def test_create_simple_step_with_category(admin_client, category):
    response = admin_client.post(
        "/settings/wizard/create",
        query_string={"simple": 1},
        data={
            "category": category,
            "title": "Bundle Step",
            "markdown": "# Bundle\nFor bundles",
            "require_interaction": False,
        },
        follow_redirects=False,
    )

    assert response.status_code == 302

    # Simple steps use 'custom' server_type
    step = WizardStep.query.filter_by(server_type="custom", category=category).first()
    assert step is not None
    assert step.title == "Bundle Step"


def test_edit_simple_step_category(admin_client, session):
    """Test editing a simple step's category."""
    # Create a simple step with post_invite category
    step = WizardStep(
        server_type="custom",
        category="post_invite",
        position=0,
        title="Simple Step",
        markdown="# Simple",
    )
    session.add(step)
    session.commit()
    step_id = step.id

    # Edit to change category to pre_invite
    response = admin_client.post(
        f"/settings/wizard/{step_id}/edit",
        data={
            "category": "pre_invite",
            "title": "Simple Step Updated",
            "markdown": "# Simple Updated",
            "require_interaction": False,
        },
        follow_redirects=False,
    )

    assert response.status_code == 302

    # Verify category was changed
    session.expire_all()
    updated_step = db.session.get(WizardStep, step_id)
    assert updated_step is not None
    assert updated_step.category == "pre_invite"
    assert updated_step.server_type == "custom"


# ─── Test Step Modal Layout ───────────────────────────────────────────


def test_create_step_modal_does_not_clip_add_menu(admin_client):
    """The modal panel must not clip the "Add..." menu (issue #984)."""
    response = admin_client.get(
        "/settings/wizard/create", headers={"HX-Request": "true"}
    )

    html = response.get_data(as_text=True)
    match = re.search(
        r'<div class="([^"]*sm:max-w-3xl[^"]*)">\s*<div class="([^"]*)">', html
    )
    assert match is not None
    panel, inner = match.group(1).split(), match.group(2).split()
    assert "overflow-hidden" not in panel
    # Without the clip, the inner block must round its own corners.
    assert "rounded-lg" in panel
    assert "rounded-lg" in inner
    assert 'x-show="open"' in html
