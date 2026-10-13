"""Tests for wizard reset service (app/services/wizard_reset.py).

This test suite verifies that the wizard reset service correctly handles the
category field when resetting wizard steps to defaults.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from app.extensions import db
from app.models import WizardStep
from app.services.wizard_reset import WizardResetService


def _write_default_steps(base_dir, server_type: str, *titles: str) -> None:
    """Write one default step file with front matter for each title."""
    server_dir = base_dir / server_type
    server_dir.mkdir()
    for number, title in enumerate(titles, start=1):
        (server_dir / f"{number:02d}.md").write_text(
            f"---\ntitle: {title}\n---\n\n# {title}\n"
        )


def _add_step(session, server_type: str, category: str, position: int, title: str):
    session.add(
        WizardStep(
            server_type=server_type,
            category=category,
            position=position,
            title=title,
            markdown=f"# {title}",
        )
    )
    session.commit()


def _titles(server_type: str, category: str) -> list[str | None]:
    steps = (
        WizardStep.query.filter_by(server_type=server_type, category=category)
        .order_by(WizardStep.position)
        .all()
    )
    return [s.title for s in steps]


@pytest.fixture
def service(app, session, tmp_path):
    """Return a reset service that reads the default steps from tmp_path."""
    with app.test_request_context():
        service = WizardResetService()
        service.base_dir = tmp_path
        yield service


class TestWizardResetService:
    """Test WizardResetService class."""

    @pytest.mark.parametrize(
        ("front_matter", "title", "requires"),
        [
            (
                "title: Test Title\nrequires:\n  - setting1\n  - setting2",
                "Test Title",
                ["setting1", "setting2"],
            ),
            ("requires: []", "Content Header", []),
        ],
    )
    def test_parse_markdown(self, service, tmp_path, front_matter, title, requires):
        """The title comes from the front matter, else from the first header."""
        md_file = tmp_path / "test.md"
        md_file.write_text(
            f"---\n{front_matter}\n---\n\n# Content Header\n\nThis is the content.\n"
        )

        result = service._parse_markdown(md_file)

        assert result["title"] == title
        assert result["markdown"] == "# Content Header\n\nThis is the content."
        assert result["requires"] == requires

    def test_get_default_steps_for_nonexistent_server(self, service):
        with pytest.raises(ValueError, match="No default steps found"):
            service.get_default_steps_for_server("nonexistent")

    def test_reset_server_steps_with_post_invite_category(
        self, service, session, tmp_path
    ):
        _add_step(session, "plex", "post_invite", 0, "Custom Step 1")
        _add_step(session, "plex", "post_invite", 1, "Custom Step 2")
        _write_default_steps(tmp_path, "plex", "Welcome", "Setup")

        success, message, count = service.reset_server_steps("plex")

        assert success is True
        assert count == 2
        assert "deleted 2" in message
        assert "imported 2" in message

        # The new steps take the positions of the deleted steps.
        plex_steps = (
            WizardStep.query.filter_by(server_type="plex", category="post_invite")
            .order_by(WizardStep.position)
            .all()
        )
        assert [(s.title, s.position) for s in plex_steps] == [
            ("Welcome", 0),
            ("Setup", 1),
        ]

    def test_reset_only_affects_specified_category(self, service, session, tmp_path):
        _add_step(session, "plex", "pre_invite", 0, "Pre Step")
        _add_step(session, "plex", "post_invite", 0, "Post Step")
        _write_default_steps(tmp_path, "plex", "Welcome")

        success, _message, _count = service.reset_server_steps(
            "plex", category="post_invite"
        )

        assert success is True
        assert _titles("plex", "pre_invite") == ["Pre Step"]
        assert _titles("plex", "post_invite") == ["Welcome"]

    def test_reset_server_steps_with_no_default_steps(self, service, session, tmp_path):
        _add_step(session, "emby", "post_invite", 0, "Custom Step")
        # An empty folder has no default steps.
        (tmp_path / "emby").mkdir()

        success, message, count = service.reset_server_steps("emby")

        assert success is False
        assert count == 0
        assert "No default steps found" in message
        # The rollback keeps the custom step.
        assert _titles("emby", "post_invite") == ["Custom Step"]

    def test_reset_server_steps_handles_database_error(self, service, tmp_path):
        _write_default_steps(tmp_path, "plex", "Welcome")

        with patch.object(db.session, "commit", side_effect=Exception("DB Error")):
            success, message, count = service.reset_server_steps("plex")

        assert success is False
        assert count == 0
        assert "Failed to reset steps" in message

    def test_reset_with_multiple_server_types(self, service, session, tmp_path):
        _add_step(session, "plex", "post_invite", 0, "Plex Step")
        _add_step(session, "jellyfin", "post_invite", 0, "Jellyfin Step")
        _write_default_steps(tmp_path, "plex", "Welcome")

        success, _message, _count = service.reset_server_steps("plex")

        assert success is True
        assert _titles("plex", "post_invite") == ["Welcome"]
        assert _titles("jellyfin", "post_invite") == ["Jellyfin Step"]


class TestWizardResetRouteHandler:
    """Test the wizard_admin reset route handler."""

    def test_reset_route_resets_both_categories(self, admin_client, session, tmp_path):
        """The route resets BOTH pre_invite and post_invite steps.

        This is the key test for the bug fix: the route handler must reset
        all steps for a server type, not only the post_invite steps.
        """
        _add_step(session, "plex", "pre_invite", 0, "Custom Pre Step")
        _add_step(session, "plex", "post_invite", 0, "Custom Post Step")
        _write_default_steps(tmp_path, "plex", "Welcome", "Setup")

        original_init = WizardResetService.__init__

        def init_with_tmp_path(self):
            original_init(self)
            self.base_dir = tmp_path

        with patch.object(WizardResetService, "__init__", init_with_tmp_path):
            response = admin_client.post(
                "/settings/wizard/reset/plex", follow_redirects=True
            )

        assert response.status_code == 200
        # No default pre_invite steps exist, so the route only deletes them.
        assert _titles("plex", "pre_invite") == []
        assert _titles("plex", "post_invite") == ["Welcome", "Setup"]
