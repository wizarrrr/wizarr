"""Tests for wizard seed service (app/services/wizard_seed.py).

This test suite verifies that the wizard seed service correctly imports default
wizard steps with the category field set to 'post_invite'.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.models import WizardStep
from app.services.wizard_seed import (
    _collect_server_files,
    _parse_markdown,
    import_default_wizard_steps,
)


def _write_default_steps(base_dir, server_type: str, *titles: str) -> None:
    """Write one default step file with front matter for each title."""
    server_dir = base_dir / server_type
    server_dir.mkdir()
    for number, title in enumerate(titles, start=1):
        (server_dir / f"{number:02d}.md").write_text(
            f"---\ntitle: {title}\n---\n\n# {title}\n"
        )


@pytest.fixture
def seed_from(app, session, monkeypatch):
    """Let the seed run (TESTING is off) and read the steps from a folder."""
    monkeypatch.setitem(app.config, "TESTING", False)

    def use_folder(base_dir) -> None:
        monkeypatch.setattr("app.services.wizard_seed.BASE_DIR", base_dir)

    return use_folder


class TestWizardSeedHelpers:
    """Test helper functions in wizard_seed.py."""

    def test_parse_markdown_with_title_in_frontmatter(self, tmp_path):
        """Test parsing markdown file with title in frontmatter."""
        md_file = tmp_path / "test.md"
        md_file.write_text(
            """---
title: Test Title
requires:
  - setting1
  - setting2
---

# Content Header

This is the content.
"""
        )

        result = _parse_markdown(md_file)

        assert result["title"] == "Test Title"
        # Note: frontmatter strips trailing newline from content
        assert result["markdown"] == "# Content Header\n\nThis is the content."
        assert result["requires"] == ["setting1", "setting2"]

    def test_parse_markdown_without_title_derives_from_header(self, tmp_path):
        """Test parsing markdown file without title in frontmatter."""
        md_file = tmp_path / "test.md"
        md_file.write_text(
            """---
requires: []
---

# Derived Title

This is the content.
"""
        )

        result = _parse_markdown(md_file)

        assert result["title"] == "Derived Title"
        # Note: frontmatter strips trailing newline from content
        assert result["markdown"] == "# Derived Title\n\nThis is the content."
        assert result["requires"] == []

    def test_parse_markdown_no_requires(self, tmp_path):
        """Test parsing markdown file without requires field."""
        _write_default_steps(tmp_path, "plex", "Test")

        result = _parse_markdown(tmp_path / "plex" / "01.md")

        assert result["title"] == "Test"
        assert result["requires"] == []

    def test_collect_server_files(self, tmp_path):
        """Test collecting markdown files organized by server type."""
        _write_default_steps(tmp_path, "plex", "Welcome", "Setup")
        _write_default_steps(tmp_path, "jellyfin", "Intro")

        result = _collect_server_files(tmp_path)

        assert set(result) == {"plex", "jellyfin"}
        assert len(result["plex"]) == 2
        assert len(result["jellyfin"]) == 1

    def test_collect_server_files_nonexistent_directory(self, tmp_path):
        """Test collecting files from non-existent directory."""
        assert _collect_server_files(tmp_path / "nonexistent") == {}


class TestImportDefaultWizardSteps:
    """Test the main import_default_wizard_steps() function."""

    def test_import_skipped_during_testing(self, app, session):
        """Test that import is skipped when TESTING config is True."""
        assert app.config.get("TESTING") is True

        # The bundled wizard_steps folder has files, but the seed must skip.
        import_default_wizard_steps()

        assert WizardStep.query.count() == 0

    def test_import_skipped_when_table_does_not_exist(self, seed_from, tmp_path):
        _write_default_steps(tmp_path, "plex", "Welcome")
        seed_from(tmp_path)

        with patch("app.services.wizard_seed.inspect") as mock_inspect:
            mock_inspect.return_value = MagicMock(
                has_table=MagicMock(return_value=False)
            )
            import_default_wizard_steps()

        mock_inspect.return_value.has_table.assert_called_once_with("wizard_step")
        assert WizardStep.query.count() == 0

    def test_fresh_install_imports_all_steps_with_post_invite_category(
        self, seed_from, tmp_path
    ):
        _write_default_steps(tmp_path, "plex", "Welcome", "Setup")
        _write_default_steps(tmp_path, "jellyfin", "Introduction")
        seed_from(tmp_path)

        import_default_wizard_steps()

        steps = WizardStep.query.order_by(
            WizardStep.server_type, WizardStep.position
        ).all()
        assert [(s.server_type, s.position, s.title, s.category) for s in steps] == [
            ("jellyfin", 0, "Introduction", "post_invite"),
            ("plex", 0, "Welcome", "post_invite"),
            ("plex", 1, "Setup", "post_invite"),
        ]

    def test_upgrade_only_imports_new_server_types(self, seed_from, session, tmp_path):
        session.add(
            WizardStep(
                server_type="plex",
                category="post_invite",
                position=0,
                title="Existing Step",
                markdown="# Existing",
            )
        )
        session.commit()
        _write_default_steps(tmp_path, "plex", "Welcome")
        _write_default_steps(tmp_path, "jellyfin", "Introduction")
        seed_from(tmp_path)

        import_default_wizard_steps()

        # Plex already has steps, so the seed does not change them.
        plex_steps = WizardStep.query.filter_by(server_type="plex").all()
        assert [s.title for s in plex_steps] == ["Existing Step"]

        # Jellyfin is a new server type, so the seed imports its steps.
        jellyfin_steps = WizardStep.query.filter_by(server_type="jellyfin").all()
        assert [(s.title, s.category) for s in jellyfin_steps] == [
            ("Introduction", "post_invite")
        ]

    def test_no_duplicate_steps_on_multiple_imports(self, seed_from, tmp_path):
        _write_default_steps(tmp_path, "plex", "Welcome")
        seed_from(tmp_path)

        import_default_wizard_steps()
        import_default_wizard_steps()

        assert WizardStep.query.filter_by(server_type="plex").count() == 1
