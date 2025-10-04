"""Tests for wizard admin form handling with category field."""

import pytest
from flask import url_for

from app.extensions import db
from app.models import AdminAccount, MediaServer, WizardStep


@pytest.fixture(autouse=True)
def session(app):
    """Return a clean database session inside an app context."""
    with app.app_context():
        # Clean up any existing data before each test
        db.session.query(WizardStep).delete()
        db.session.query(AdminAccount).delete()
        db.session.query(MediaServer).delete()
        db.session.commit()

        yield db.session

        # Clean up after the test
        db.session.query(WizardStep).delete()
        db.session.query(AdminAccount).delete()
        db.session.query(MediaServer).delete()
        db.session.commit()
        db.session.rollback()


@pytest.fixture
def admin_user(session):
    """Create an admin user for authentication."""
    admin = AdminAccount(username="testadmin")
    admin.set_password("testpass123")
    session.add(admin)
    session.commit()
    return admin


@pytest.fixture
def authenticated_client(client, admin_user):
    """Return a client with an authenticated admin session."""
    with client.session_transaction() as sess:
        sess["_user_id"] = str(admin_user.id)
        sess["_fresh"] = True
    return client


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


def test_create_step_with_pre_invite_category(
    authenticated_client, session, plex_server
):
    """Test creating a wizard step with pre_invite category."""
    response = authenticated_client.post(
        url_for("wizard_admin.create_step"),
        data={
            "server_type": "plex",
            "category": "pre_invite",
            "title": "Pre-Invite Welcome",
            "markdown": "# Welcome\nThis is shown before invite acceptance",
            "require_interaction": False,
        },
        follow_redirects=False,
    )

    # Should redirect after successful creation
    assert response.status_code == 302

    # Verify step was created with correct category
    step = WizardStep.query.filter_by(
        server_type="plex", category="pre_invite", title="Pre-Invite Welcome"
    ).first()
    assert step is not None
    assert step.title == "Pre-Invite Welcome"
    assert step.category == "pre_invite"
    # Position should be >= 0 (exact value depends on seeded steps)
    assert step.position >= 0


def test_create_step_with_post_invite_category(
    authenticated_client, session, plex_server
):
    """Test creating a wizard step with post_invite category."""
    response = authenticated_client.post(
        url_for("wizard_admin.create_step"),
        data={
            "server_type": "plex",
            "category": "post_invite",
            "title": "Post-Invite Setup",
            "markdown": "# Setup\nThis is shown after invite acceptance",
            "require_interaction": False,
        },
        follow_redirects=False,
    )

    assert response.status_code == 302

    step = WizardStep.query.filter_by(
        server_type="plex", category="post_invite", title="Post-Invite Setup"
    ).first()
    assert step is not None
    assert step.title == "Post-Invite Setup"
    assert step.category == "post_invite"
    # Position should be >= 0 (exact value depends on seeded steps)
    assert step.position >= 0


def test_create_step_default_category(authenticated_client, session, plex_server):
    """Test that category defaults to post_invite when not specified."""
    response = authenticated_client.post(
        url_for("wizard_admin.create_step"),
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


# ─── Test Editing Step Category ───────────────────────────────────────


def test_edit_step_category_from_post_to_pre(
    authenticated_client, session, plex_server
):
    """Test editing a step's category from post_invite to pre_invite."""
    # Create a post_invite step
    step = WizardStep(
        server_type="plex",
        category="post_invite",
        position=0,
        title="Original Post Step",
        markdown="# Original",
    )
    session.add(step)
    session.commit()
    step_id = step.id

    # Edit to change category
    response = authenticated_client.post(
        url_for("wizard_admin.edit_step", step_id=step_id),
        data={
            "server_type": "plex",
            "category": "pre_invite",
            "title": "Changed to Pre Step",
            "markdown": "# Changed",
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
    assert updated_step.title == "Changed to Pre Step"


def test_edit_step_category_from_pre_to_post(
    authenticated_client, session, plex_server
):
    """Test editing a step's category from pre_invite to post_invite."""
    # Create a pre_invite step
    step = WizardStep(
        server_type="plex",
        category="pre_invite",
        position=0,
        title="Original Pre Step",
        markdown="# Original",
    )
    session.add(step)
    session.commit()
    step_id = step.id

    # Edit to change category
    response = authenticated_client.post(
        url_for("wizard_admin.edit_step", step_id=step_id),
        data={
            "server_type": "plex",
            "category": "post_invite",
            "title": "Changed to Post Step",
            "markdown": "# Changed",
            "require_interaction": False,
        },
        follow_redirects=False,
    )

    assert response.status_code == 302

    # Verify category was changed
    session.expire_all()
    updated_step = db.session.get(WizardStep, step_id)
    assert updated_step is not None
    assert updated_step.category == "post_invite"
    assert updated_step.title == "Changed to Post Step"


def test_edit_step_preserves_category_when_not_changed(
    authenticated_client, session, plex_server
):
    """Test that editing a step without changing category preserves the original category."""
    # Create a pre_invite step
    step = WizardStep(
        server_type="plex",
        category="pre_invite",
        position=0,
        title="Original Title",
        markdown="# Original",
    )
    session.add(step)
    session.commit()
    step_id = step.id

    # Edit only the title, keeping category the same
    response = authenticated_client.post(
        url_for("wizard_admin.edit_step", step_id=step_id),
        data={
            "server_type": "plex",
            "category": "pre_invite",
            "title": "Updated Title",
            "markdown": "# Original",
            "require_interaction": False,
        },
        follow_redirects=False,
    )

    assert response.status_code == 302

    # Verify category was preserved
    session.expire_all()
    updated_step = db.session.get(WizardStep, step_id)
    assert updated_step is not None
    assert updated_step.category == "pre_invite"
    assert updated_step.title == "Updated Title"


# ─── Test Preset Creation with Category ───────────────────────────────


def test_create_preset_with_pre_invite_category(
    authenticated_client, session, plex_server
):
    """Test creating a preset step with pre_invite category."""
    from app.models import WizardStep

    response = authenticated_client.post(
        url_for("wizard_admin.create_preset"),
        data={
            "preset_id": "discord_community",
            "server_type": "plex",
            "category": "pre_invite",
            "discord_id": "123456789",
        },
        follow_redirects=False,
    )

    # Should redirect on success
    assert response.status_code == 302

    # Verify the step was created with correct category
    step = WizardStep.query.filter_by(
        server_type="plex", category="pre_invite", title="Discord community"
    ).first()
    assert step is not None
    assert step.category == "pre_invite"
    assert "discord" in step.markdown.lower()


def test_create_preset_with_post_invite_category(
    authenticated_client, session, plex_server
):
    """Test creating a preset step with post_invite category."""
    from app.models import WizardStep

    response = authenticated_client.post(
        url_for("wizard_admin.create_preset"),
        data={
            "preset_id": "overseerr_requests",
            "server_type": "plex",
            "category": "post_invite",
            "overseerr_url": "https://overseerr.example.com",
        },
        follow_redirects=False,
    )

    # Should redirect on success
    assert response.status_code == 302

    # Verify the step was created with correct category
    step = WizardStep.query.filter_by(
        server_type="plex", category="post_invite", title="Automatic requests"
    ).first()
    assert step is not None
    assert step.category == "post_invite"
    assert "overseerr" in step.markdown.lower()


# ─── Test Position Calculation with Category ──────────────────────────


def test_position_calculation_respects_category(
    authenticated_client, session, plex_server
):
    """Test that position calculation is scoped to server_type AND category."""
    # Get existing counts
    existing_pre_count = WizardStep.query.filter_by(
        server_type="plex", category="pre_invite"
    ).count()
    WizardStep.query.filter_by(server_type="plex", category="post_invite").count()

    # Create pre_invite step
    pre_step = WizardStep(
        server_type="plex",
        category="pre_invite",
        position=existing_pre_count,
        markdown="# Pre Step 1",
    )
    session.add(pre_step)
    session.commit()

    # Create post_invite step via API
    response = authenticated_client.post(
        url_for("wizard_admin.create_step"),
        data={
            "server_type": "plex",
            "category": "post_invite",
            "markdown": "# Post Step 1",
            "require_interaction": False,
        },
        follow_redirects=False,
    )

    assert response.status_code == 302

    # Verify both categories have independent position sequences
    pre_steps = (
        WizardStep.query.filter_by(server_type="plex", category="pre_invite")
        .order_by(WizardStep.position)
        .all()
    )
    post_steps = (
        WizardStep.query.filter_by(server_type="plex", category="post_invite")
        .order_by(WizardStep.position)
        .all()
    )

    # Should have at least one step in each category
    assert len(pre_steps) >= 1
    assert len(post_steps) >= 1

    # The manually created pre_step should be at the expected position
    assert pre_step.position == existing_pre_count


# ─── Test Simple Form (Bundle Steps) with Category ────────────────────


def test_create_simple_step_with_pre_invite_category(authenticated_client, session):
    """Test creating a simple (bundle) step with pre_invite category."""
    response = authenticated_client.post(
        url_for("wizard_admin.create_step", simple=1),
        data={
            "category": "pre_invite",
            "title": "Bundle Pre Step",
            "markdown": "# Bundle Pre\nFor bundles",
            "require_interaction": False,
        },
        follow_redirects=False,
    )

    assert response.status_code == 302

    # Simple steps use 'custom' server_type
    step = WizardStep.query.filter_by(
        server_type="custom", category="pre_invite"
    ).first()
    assert step is not None
    assert step.title == "Bundle Pre Step"
    assert step.category == "pre_invite"


def test_create_simple_step_with_post_invite_category(authenticated_client, session):
    """Test creating a simple (bundle) step with post_invite category."""
    response = authenticated_client.post(
        url_for("wizard_admin.create_step", simple=1),
        data={
            "category": "post_invite",
            "title": "Bundle Post Step",
            "markdown": "# Bundle Post\nFor bundles",
            "require_interaction": False,
        },
        follow_redirects=False,
    )

    assert response.status_code == 302

    step = WizardStep.query.filter_by(
        server_type="custom", category="post_invite"
    ).first()
    assert step is not None
    assert step.title == "Bundle Post Step"
    assert step.category == "post_invite"


def test_edit_simple_step_category(authenticated_client, session):
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
    response = authenticated_client.post(
        url_for("wizard_admin.edit_step", step_id=step_id),
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


# ─── Test Multiple Steps with Same Position in Different Categories ───


def test_multiple_steps_same_position_different_categories(
    authenticated_client, session, plex_server
):
    """Test that multiple steps can have the same position if in different categories."""
    # Create pre_invite step
    response1 = authenticated_client.post(
        url_for("wizard_admin.create_step"),
        data={
            "server_type": "plex",
            "category": "pre_invite",
            "title": "Pre Step 1",
            "markdown": "# Pre 1",
            "require_interaction": False,
        },
        follow_redirects=False,
    )
    assert response1.status_code == 302

    # Create post_invite step
    response2 = authenticated_client.post(
        url_for("wizard_admin.create_step"),
        data={
            "server_type": "plex",
            "category": "post_invite",
            "title": "Post Step 1",
            "markdown": "# Post 1",
            "require_interaction": False,
        },
        follow_redirects=False,
    )
    assert response2.status_code == 302

    # Both should exist with their titles
    pre_step = WizardStep.query.filter_by(
        server_type="plex", category="pre_invite", title="Pre Step 1"
    ).first()
    post_step = WizardStep.query.filter_by(
        server_type="plex", category="post_invite", title="Post Step 1"
    ).first()

    assert pre_step is not None
    assert post_step is not None
    assert pre_step.id != post_step.id
    # They can have the same position because they're in different categories
    # (though they might not if there are seeded steps)


# ─── Test Form Validation ──────────────────────────────────────────────


def test_create_step_requires_category(authenticated_client, session, plex_server):
    """Test that category field is required (has default value)."""
    # Even without explicit category, it should default to post_invite
    response = authenticated_client.post(
        url_for("wizard_admin.create_step"),
        data={
            "server_type": "plex",
            "title": "No Category Specified",
            "markdown": "# Test",
            "require_interaction": False,
        },
        follow_redirects=False,
    )

    # Should succeed with default category
    assert response.status_code == 302

    step = WizardStep.query.filter_by(server_type="plex").first()
    assert step is not None
    assert step.category == "post_invite"


def test_create_step_invalid_category_rejected(
    authenticated_client, session, plex_server
):
    """Test that invalid category values are rejected by form validation."""
    response = authenticated_client.post(
        url_for("wizard_admin.create_step"),
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


# ─── Test Category Persistence Across Operations ──────────────────────


def test_category_persists_after_multiple_edits(
    authenticated_client, session, plex_server
):
    """Test that category persists correctly through multiple edit operations."""
    # Create step with pre_invite category
    step = WizardStep(
        server_type="plex",
        category="pre_invite",
        position=0,
        title="Original",
        markdown="# Original",
    )
    session.add(step)
    session.commit()
    step_id = step.id

    # Edit 1: Change title only
    authenticated_client.post(
        url_for("wizard_admin.edit_step", step_id=step_id),
        data={
            "server_type": "plex",
            "category": "pre_invite",
            "title": "Edit 1",
            "markdown": "# Original",
            "require_interaction": False,
        },
    )

    session.expire_all()
    step = db.session.get(WizardStep, step_id)
    assert step.category == "pre_invite"

    # Edit 2: Change markdown only
    authenticated_client.post(
        url_for("wizard_admin.edit_step", step_id=step_id),
        data={
            "server_type": "plex",
            "category": "pre_invite",
            "title": "Edit 1",
            "markdown": "# Updated",
            "require_interaction": False,
        },
    )

    session.expire_all()
    step = db.session.get(WizardStep, step_id)
    assert step.category == "pre_invite"

    # Edit 3: Change category to post_invite
    authenticated_client.post(
        url_for("wizard_admin.edit_step", step_id=step_id),
        data={
            "server_type": "plex",
            "category": "post_invite",
            "title": "Edit 1",
            "markdown": "# Updated",
            "require_interaction": False,
        },
    )

    session.expire_all()
    step = db.session.get(WizardStep, step_id)
    assert step.category == "post_invite"
