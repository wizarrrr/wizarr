"""Tests for wizard seed service (app/services/wizard_seed.py).

This test suite verifies that the wizard seed service correctly imports default
wizard steps with the category field set to 'post_invite' and handles the new
unique constraint (server_type, category, position).
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.extensions import db
from app.models import WizardStep
from app.services.wizard_seed import (
    _collect_server_files,
    _gather_step_files,
    _parse_markdown,
    import_default_wizard_steps,
)


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
        md_file = tmp_path / "test.md"
        md_file.write_text(
            """---
title: Test
---

# Content
"""
        )

        result = _parse_markdown(md_file)

        assert result["title"] == "Test"
        assert result["requires"] == []

    def test_collect_server_files(self, tmp_path):
        """Test collecting markdown files organized by server type."""
        # Create directory structure
        plex_dir = tmp_path / "plex"
        plex_dir.mkdir()
        (plex_dir / "01-welcome.md").write_text("# Welcome")
        (plex_dir / "02-setup.md").write_text("# Setup")

        jellyfin_dir = tmp_path / "jellyfin"
        jellyfin_dir.mkdir()
        (jellyfin_dir / "01-intro.md").write_text("# Intro")

        result = _collect_server_files(tmp_path)

        assert "plex" in result
        assert "jellyfin" in result
        assert len(result["plex"]) == 2
        assert len(result["jellyfin"]) == 1

    def test_collect_server_files_nonexistent_directory(self, tmp_path):
        """Test collecting files from non-existent directory."""
        nonexistent = tmp_path / "nonexistent"
        result = _collect_server_files(nonexistent)

        assert result == {}

    def test_gather_step_files_empty_directory(self, tmp_path):
        """Test gathering step files from empty directory."""
        with patch("app.services.wizard_seed.BASE_DIR", tmp_path):
            result = _gather_step_files()
            assert result == []


class TestImportDefaultWizardSteps:
    """Test the main import_default_wizard_steps() function."""

    def test_import_skipped_during_testing(self, app):
        """Test that import is skipped when TESTING config is True."""
        with app.app_context():
            # TESTING should be True in test environment
            assert app.config.get("TESTING") is True

            # Get count before import
            count_before = WizardStep.query.count()

            # Should return early without doing anything
            import_default_wizard_steps()

            # Verify no NEW steps were created
            count_after = WizardStep.query.count()
            assert count_after == count_before

    def test_import_skipped_when_table_does_not_exist(self, app):
        """Test that import is skipped when wizard_step table doesn't exist."""
        with (
            app.app_context(),
            patch("app.services.wizard_seed.inspect") as mock_inspect,
        ):
            mock_inspector = MagicMock()
            mock_inspector.has_table.return_value = False
            mock_inspect.return_value = mock_inspector

            # Temporarily disable TESTING to allow function to proceed
            original_testing = app.config["TESTING"]
            app.config["TESTING"] = False

            try:
                import_default_wizard_steps()
                # Should return early without error
            except Exception as e:
                pytest.fail(f"Should not raise exception: {e}")
            finally:
                app.config["TESTING"] = original_testing

    def test_fresh_install_imports_all_steps_with_post_invite_category(
        self, app, tmp_path
    ):
        """Test that fresh install imports all steps with category='post_invite'."""
        with app.app_context():
            # Clean up any existing steps first to simulate fresh install
            WizardStep.query.delete()
            db.session.commit()
            # Create mock wizard steps directory
            plex_dir = tmp_path / "plex"
            plex_dir.mkdir()
            (plex_dir / "01-welcome.md").write_text(
                """---
title: Welcome
---

# Welcome to Plex
"""
            )
            (plex_dir / "02-setup.md").write_text(
                """---
title: Setup
---

# Setup Instructions
"""
            )

            jellyfin_dir = tmp_path / "jellyfin"
            jellyfin_dir.mkdir()
            (jellyfin_dir / "01-intro.md").write_text(
                """---
title: Introduction
---

# Welcome to Jellyfin
"""
            )

            # Patch BASE_DIR and disable TESTING
            with patch("app.services.wizard_seed.BASE_DIR", tmp_path):
                original_testing = app.config["TESTING"]
                app.config["TESTING"] = False

                try:
                    import_default_wizard_steps()

                    # Verify steps were imported
                    plex_steps = (
                        WizardStep.query.filter_by(server_type="plex")
                        .order_by(WizardStep.position)
                        .all()
                    )
                    jellyfin_steps = (
                        WizardStep.query.filter_by(server_type="jellyfin")
                        .order_by(WizardStep.position)
                        .all()
                    )

                    assert len(plex_steps) == 2
                    assert len(jellyfin_steps) == 1

                    # Verify all steps have category='post_invite'
                    for step in plex_steps + jellyfin_steps:
                        assert step.category == "post_invite", (
                            f"Step {step.id} should have category='post_invite'"
                        )

                    # Verify positions are correct
                    assert plex_steps[0].position == 0
                    assert plex_steps[0].title == "Welcome"
                    assert plex_steps[1].position == 1
                    assert plex_steps[1].title == "Setup"

                    assert jellyfin_steps[0].position == 0
                    assert jellyfin_steps[0].title == "Introduction"

                finally:
                    app.config["TESTING"] = original_testing

    def test_upgrade_only_imports_new_server_types(self, app, tmp_path):
        """Test that upgrade only imports steps for new server types."""
        with app.app_context():
            # Clean up any existing steps first
            WizardStep.query.delete()
            db.session.commit()

            # Create existing plex step
            existing_step = WizardStep(
                server_type="plex",
                category="post_invite",
                position=0,
                title="Existing Step",
                markdown="# Existing",
            )
            db.session.add(existing_step)
            db.session.commit()

            # Create mock wizard steps directory with plex and jellyfin
            plex_dir = tmp_path / "plex"
            plex_dir.mkdir()
            (plex_dir / "01-welcome.md").write_text(
                """---
title: Welcome
---

# Welcome to Plex
"""
            )

            jellyfin_dir = tmp_path / "jellyfin"
            jellyfin_dir.mkdir()
            (jellyfin_dir / "01-intro.md").write_text(
                """---
title: Introduction
---

# Welcome to Jellyfin
"""
            )

            # Patch BASE_DIR and disable TESTING
            with patch("app.services.wizard_seed.BASE_DIR", tmp_path):
                original_testing = app.config["TESTING"]
                app.config["TESTING"] = False

                try:
                    import_default_wizard_steps()

                    # Verify plex steps were NOT imported (already exists)
                    plex_steps = WizardStep.query.filter_by(server_type="plex").all()
                    assert len(plex_steps) == 1
                    assert plex_steps[0].title == "Existing Step"

                    # Verify jellyfin steps WERE imported (new server type)
                    jellyfin_steps = WizardStep.query.filter_by(
                        server_type="jellyfin"
                    ).all()
                    assert len(jellyfin_steps) == 1
                    assert jellyfin_steps[0].category == "post_invite"
                    assert jellyfin_steps[0].title == "Introduction"

                finally:
                    app.config["TESTING"] = original_testing

    def test_unique_constraint_with_category(self, app):
        """Test that unique constraint works with category field."""
        with app.app_context():
            # Clean up any existing steps first
            WizardStep.query.delete()
            db.session.commit()

            # Create two steps with same server_type and position but different categories
            pre_step = WizardStep(
                server_type="plex",
                category="pre_invite",
                position=0,
                title="Pre Step",
                markdown="# Pre",
            )
            post_step = WizardStep(
                server_type="plex",
                category="post_invite",
                position=0,
                title="Post Step",
                markdown="# Post",
            )

            db.session.add_all([pre_step, post_step])
            db.session.commit()

            # Both should exist without constraint violation
            steps = WizardStep.query.filter_by(server_type="plex").all()
            assert len(steps) == 2

    def test_no_duplicate_steps_on_multiple_imports(self, app, tmp_path):
        """Test that running import multiple times doesn't duplicate steps."""
        with app.app_context():
            # Clean up any existing steps first
            WizardStep.query.delete()
            db.session.commit()

            # Create mock wizard steps directory
            plex_dir = tmp_path / "plex"
            plex_dir.mkdir()
            (plex_dir / "01-welcome.md").write_text(
                """---
title: Welcome
---

# Welcome
"""
            )

            with patch("app.services.wizard_seed.BASE_DIR", tmp_path):
                original_testing = app.config["TESTING"]
                app.config["TESTING"] = False

                try:
                    # Run import twice
                    import_default_wizard_steps()
                    import_default_wizard_steps()

                    # Should only have one step (second import should be a no-op)
                    plex_steps = WizardStep.query.filter_by(server_type="plex").all()
                    assert len(plex_steps) == 1

                finally:
                    app.config["TESTING"] = original_testing
