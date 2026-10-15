"""Tests for wizard rendering logic (_serve_wizard function).

This module tests the _serve_wizard() function to ensure:
- HTMX partial rendering vs full page rendering works
- Interaction requirement detection works
- Phase parameter is passed to templates
"""

import pytest

from app.models import MediaServer, WizardStep


@pytest.fixture
def sample_wizard_steps(session):
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

    session.add_all(steps)
    session.commit()

    return steps


@pytest.fixture
def sample_media_server(session):
    """Create a sample media server for testing."""
    server = MediaServer(
        name="Test Plex Server",
        server_type="plex",
        url="http://localhost:32400",
        external_url="https://plex.example.com",
    )
    session.add(server)
    session.commit()
    return server


def _serve_plex(app, category: str, idx: int, *, phase: str = "pre", htmx=False):
    """Call _serve_wizard() for the Plex steps of one category."""
    from app.blueprints.wizard.routes import _serve_wizard, _settings, _steps

    headers = {"HX-Request": "true"} if htmx else {}
    with app.test_request_context(headers=headers):
        steps = _steps("plex", _settings(), category=category)
        return _serve_wizard("plex", idx, steps, phase=phase)


@pytest.mark.usefixtures("sample_wizard_steps", "sample_media_server")
class TestServeWizardFunction:
    """Test the _serve_wizard() function with different phases."""

    @pytest.mark.parametrize(
        ("category", "phase", "content"),
        [
            ("pre_invite", "pre", "Before you join"),
            ("post_invite", "post", "Welcome to Plex!"),
        ],
    )
    def test_full_page_render_passes_phase(self, app, category, phase, content):
        response = _serve_plex(app, category, 0, phase=phase)

        # A request without HX-Request gets the full page as a string.
        assert isinstance(response, str)
        assert "<html" in response
        assert f'data-phase="{phase}"' in response
        assert content in response

    def test_serve_wizard_htmx_partial_rendering(self, app):
        response = _serve_plex(app, "pre_invite", 0, htmx=True)

        assert response.headers["X-Wizard-Idx"] == "0"
        assert "<html" not in response.get_data(as_text=True)

    def test_serve_wizard_interaction_requirement_detection(self, app):
        first = _serve_plex(app, "pre_invite", 0, htmx=True)
        assert first.headers["X-Require-Interaction"] == "false"

        second = _serve_plex(app, "pre_invite", 1, htmx=True)
        assert second.headers["X-Require-Interaction"] == "true"

    @pytest.mark.parametrize(("idx", "clamped"), [(-5, "0"), (999, "1")])
    def test_serve_wizard_clamps_index_to_valid_range(self, app, idx, clamped):
        response = _serve_plex(app, "pre_invite", idx, htmx=True)

        assert response.headers["X-Wizard-Idx"] == clamped


def test_serve_wizard_handles_empty_steps(app, sample_media_server):
    """An empty steps list gives a 404."""
    from werkzeug.exceptions import NotFound

    from app.blueprints.wizard.routes import _serve_wizard

    with app.test_request_context(), pytest.raises(NotFound):
        _serve_wizard("plex", 0, [], phase="pre")
