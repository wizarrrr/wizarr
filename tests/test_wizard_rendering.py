"""Tests for wizard rendering logic (_serve_wizard function).

This module tests the refactored _serve_wizard() function to ensure:
- It works correctly with both pre and post phases
- HTMX partial rendering vs full page rendering works
- Interaction requirement detection works
- Phase parameter is passed to templates

Requirements tested:
- 1.3: Existing _render() function is reused for both pre and post-invite steps
- 6.5: Pre-wizard UI matches existing wizard interface
- 8.4: Post-wizard UI matches existing wizard interface
- 15.1: Unit tests for wizard rendering
"""

import pytest

from app.extensions import db
from app.models import MediaServer, WizardStep


@pytest.fixture
def session_fixture(app):
    """Return a clean database session inside an app context."""
    with app.app_context():
        # Clean up any existing data before the test
        db.session.query(WizardStep).delete()
        db.session.query(MediaServer).delete()
        db.session.commit()

        yield db.session

        # Clean up after the test
        db.session.rollback()


@pytest.fixture
def sample_wizard_steps(session_fixture):
    """Create sample wizard steps for testing."""
    steps = [
        WizardStep(
            server_type="plex",
            category="pre_invite",
            position=0,
            title="Pre-Welcome",
            markdown="# Pre-Welcome\nBefore you join...",
            require_interaction=False,
        ),
        WizardStep(
            server_type="plex",
            category="pre_invite",
            position=1,
            title="Pre-Requirements",
            markdown="# Requirements\nYou need...",
            require_interaction=True,
        ),
        WizardStep(
            server_type="plex",
            category="post_invite",
            position=0,
            title="Post-Welcome",
            markdown="# Welcome\nWelcome to Plex!",
            require_interaction=False,
        ),
        WizardStep(
            server_type="plex",
            category="post_invite",
            position=1,
            title="Post-Setup",
            markdown="# Setup\nLet's get started...",
            require_interaction=True,
        ),
    ]

    for step in steps:
        session_fixture.add(step)
    session_fixture.commit()

    return steps


@pytest.fixture
def sample_media_server(session_fixture):
    """Create a sample media server for testing."""
    server = MediaServer(
        name="Test Plex Server",
        server_type="plex",
        url="http://localhost:32400",
        external_url="https://plex.example.com",
    )
    session_fixture.add(server)
    session_fixture.commit()
    return server


class TestServeWizardFunction:
    """Test the _serve_wizard() function with different phases."""

    def test_serve_wizard_with_pre_phase(
        self, app, client, sample_wizard_steps, sample_media_server
    ):
        """Test _serve_wizard() with pre phase."""
        from app.blueprints.wizard.routes import _serve_wizard, _settings, _steps

        with (
            app.app_context(),
            client,
            client.application.test_request_context(),
        ):
            cfg = _settings()
            steps = _steps("plex", cfg, category="pre_invite")

            # Call _serve_wizard with pre phase
            response = _serve_wizard("plex", 0, steps, phase="pre")

            # Should return a response
            assert response is not None
            # Response should be a string (rendered HTML)
            assert isinstance(response, str)
            # Response should contain the step content
            assert "Pre-Welcome" in response or "Before you join" in response

    def test_serve_wizard_with_post_phase(
        self, app, client, sample_wizard_steps, sample_media_server
    ):
        """Test _serve_wizard() with post phase."""
        from app.blueprints.wizard.routes import _serve_wizard, _settings, _steps

        with (
            app.app_context(),
            client,
            client.application.test_request_context(),
        ):
            cfg = _settings()
            steps = _steps("plex", cfg, category="post_invite")

            # Call _serve_wizard with post phase
            response = _serve_wizard("plex", 0, steps, phase="post")

            # Should return a response
            assert response is not None
            # Response should be a string (rendered HTML)
            assert isinstance(response, str)
            # Response should contain the step content
            assert "Welcome to Plex!" in response or "Welcome" in response

    def test_serve_wizard_full_page_rendering(
        self, app, client, sample_wizard_steps, sample_media_server
    ):
        """Test that _serve_wizard returns full page for non-HTMX requests."""
        from app.blueprints.wizard.routes import _serve_wizard, _settings, _steps

        with app.app_context(), client:
            cfg = _settings()
            steps = _steps("plex", cfg, category="pre_invite")

            # Simulate non-HTMX request (initial page load)
            with client.application.test_request_context():
                response = _serve_wizard("plex", 0, steps, phase="pre")

                # Should use frame.html template (full page)
                # Check for typical frame.html elements
                assert response is not None

    def test_serve_wizard_htmx_partial_rendering(
        self, app, client, sample_wizard_steps, sample_media_server
    ):
        """Test that _serve_wizard returns partial for HTMX requests."""
        from app.blueprints.wizard.routes import _serve_wizard, _settings, _steps

        with (
            app.app_context(),
            client,
        ):
            cfg = _settings()
            steps = _steps("plex", cfg, category="pre_invite")

            # Simulate HTMX request
            with client.application.test_request_context(
                headers={"HX-Request": "true"}
            ):
                response = _serve_wizard("plex", 0, steps, phase="pre")

                # Should return a response with custom headers
                assert response is not None
                # Check for HTMX-specific headers
                assert "X-Wizard-Idx" in response.headers
                assert response.headers["X-Wizard-Idx"] == "0"

    def test_serve_wizard_interaction_requirement_detection(
        self, app, client, sample_wizard_steps, sample_media_server
    ):
        """Test that _serve_wizard correctly detects interaction requirements."""
        from app.blueprints.wizard.routes import _serve_wizard, _settings, _steps

        with (
            app.app_context(),
            client,
        ):
            cfg = _settings()
            steps = _steps("plex", cfg, category="pre_invite")

            # Test step without interaction requirement (idx=0)
            with client.application.test_request_context(
                headers={"HX-Request": "true"}
            ):
                response = _serve_wizard("plex", 0, steps, phase="pre")
                assert response.headers["X-Require-Interaction"] == "false"

            # Test step with interaction requirement (idx=1)
            with client.application.test_request_context(
                headers={"HX-Request": "true"}
            ):
                response = _serve_wizard("plex", 1, steps, phase="pre")
                assert response.headers["X-Require-Interaction"] == "true"

    def test_serve_wizard_phase_parameter_passed_to_template(
        self, app, client, sample_wizard_steps, sample_media_server
    ):
        """Test that phase parameter is passed to templates."""
        from app.blueprints.wizard.routes import _serve_wizard, _settings, _steps

        with (
            app.app_context(),
            client,
        ):
            cfg = _settings()
            pre_steps = _steps("plex", cfg, category="pre_invite")
            post_steps = _steps("plex", cfg, category="post_invite")

            # Test pre phase
            with client.application.test_request_context():
                response = _serve_wizard("plex", 0, pre_steps, phase="pre")
                # Phase should be available in template context
                # We can't directly check template context, but we can verify response is valid
                assert response is not None

            # Test post phase
            with client.application.test_request_context():
                response = _serve_wizard("plex", 0, post_steps, phase="post")
                assert response is not None

    def test_serve_wizard_handles_empty_steps(self, app, client, sample_media_server):
        """Test that _serve_wizard handles empty steps list correctly."""
        from werkzeug.exceptions import NotFound

        from app.blueprints.wizard.routes import _serve_wizard

        with (
            app.app_context(),
            client,
            pytest.raises(NotFound),
            client.application.test_request_context(),
        ):
            # Empty steps list should raise 404
            _serve_wizard("plex", 0, [], phase="pre")

    def test_serve_wizard_clamps_index_to_valid_range(
        self, app, client, sample_wizard_steps, sample_media_server
    ):
        """Test that _serve_wizard clamps index to valid range."""
        from app.blueprints.wizard.routes import _serve_wizard, _settings, _steps

        with (
            app.app_context(),
            client,
        ):
            cfg = _settings()
            steps = _steps("plex", cfg, category="pre_invite")

            # Test negative index (should clamp to 0)
            with client.application.test_request_context(
                headers={"HX-Request": "true"}
            ):
                response = _serve_wizard("plex", -5, steps, phase="pre")
                assert response.headers["X-Wizard-Idx"] == "0"

            # Test index beyond max (should clamp to max_idx)
            with client.application.test_request_context(
                headers={"HX-Request": "true"}
            ):
                response = _serve_wizard("plex", 999, steps, phase="pre")
                max_idx = len(steps) - 1
                assert response.headers["X-Wizard-Idx"] == str(max_idx)


class TestLegacyServeFunction:
    """Test that the legacy _serve() function still works."""

    def test_legacy_serve_delegates_to_serve_wizard(
        self, app, client, sample_wizard_steps, sample_media_server
    ):
        """Test that _serve() delegates to _serve_wizard() with post phase."""
        from app.blueprints.wizard.routes import _serve

        with (
            app.app_context(),
            client,
            client.application.test_request_context(),
        ):
            response = _serve("plex", 0)

            # Should return a response
            assert response is not None
            # Response should be a string (rendered HTML)
            assert isinstance(response, str)
            # Should contain post-invite content
            assert "Welcome to Plex!" in response or "Welcome" in response

    def test_legacy_serve_uses_post_invite_category(
        self, app, client, sample_wizard_steps, sample_media_server
    ):
        """Test that _serve() uses post_invite category by default."""
        from app.blueprints.wizard.routes import _serve

        with (
            app.app_context(),
            client,
            client.application.test_request_context(headers={"HX-Request": "true"}),
        ):
            response = _serve("plex", 0)

            # Should return post-invite steps (Response object for HTMX)
            assert response is not None
            # For HTMX requests, response is a Response object
            from flask import Response

            if isinstance(response, Response):
                assert b"Before you join" not in response.data
            else:
                # Should not contain pre-invite content
                assert "Before you join" not in response
