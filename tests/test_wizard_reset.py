"""Tests for wizard reset service (app/services/wizard_reset.py).

This test suite verifies that the wizard reset service correctly handles the
category field when resetting wizard steps to defaults.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from app.extensions import db
from app.models import AdminAccount, WizardStep
from app.services.wizard_reset import WizardResetService

# ─── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture
def session(app):
    """Provide a database session for tests."""
    with app.app_context():
        yield db.session
        db.session.rollback()


@pytest.fixture
def admin_user(session):
    """Create an admin user for authentication."""
    # Check if admin already exists
    admin = session.query(AdminAccount).filter_by(username="testadmin").first()
    if not admin:
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


class TestWizardResetService:
    """Test WizardResetService class."""

    def test_parse_markdown_with_title_in_frontmatter(self, app, tmp_path):
        """Test parsing markdown file with title in frontmatter."""
        with app.app_context():
            service = WizardResetService()
            service.base_dir = tmp_path

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

            result = service._parse_markdown(md_file)

            assert result["title"] == "Test Title"
            assert result["markdown"] == "# Content Header\n\nThis is the content."
            assert result["requires"] == ["setting1", "setting2"]

    def test_parse_markdown_without_title_derives_from_header(self, app, tmp_path):
        """Test parsing markdown file without title in frontmatter."""
        with app.app_context():
            service = WizardResetService()
            service.base_dir = tmp_path

            md_file = tmp_path / "test.md"
            md_file.write_text(
                """---
requires: []
---

# Derived Title

This is the content.
"""
            )

            result = service._parse_markdown(md_file)

            assert result["title"] == "Derived Title"
            assert result["markdown"] == "# Derived Title\n\nThis is the content."
            assert result["requires"] == []

    def test_get_default_steps_for_server_with_post_invite_category(
        self, app, tmp_path
    ):
        """Test getting default steps with post_invite category (default)."""
        with app.app_context():
            service = WizardResetService()
            service.base_dir = tmp_path

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

            steps = service.get_default_steps_for_server("plex")

            assert len(steps) == 2
            # Verify tuple structure: (title, markdown, requires, position, category)
            assert steps[0][0] == "Welcome"
            assert steps[0][3] == 0  # position
            assert steps[0][4] == "post_invite"  # category
            assert steps[1][0] == "Setup"
            assert steps[1][3] == 1  # position
            assert steps[1][4] == "post_invite"  # category

    def test_get_default_steps_for_server_with_pre_invite_category(self, app, tmp_path):
        """Test getting default steps with pre_invite category."""
        with app.app_context():
            service = WizardResetService()
            service.base_dir = tmp_path

            # Create mock wizard steps directory
            jellyfin_dir = tmp_path / "jellyfin"
            jellyfin_dir.mkdir()
            (jellyfin_dir / "01-intro.md").write_text(
                """---
title: Introduction
---

# Welcome to Jellyfin
"""
            )

            steps = service.get_default_steps_for_server(
                "jellyfin", category="pre_invite"
            )

            assert len(steps) == 1
            assert steps[0][0] == "Introduction"
            assert steps[0][3] == 0  # position
            assert steps[0][4] == "pre_invite"  # category

    def test_get_default_steps_for_nonexistent_server(self, app, tmp_path):
        """Test getting default steps for non-existent server type."""
        with app.app_context():
            service = WizardResetService()
            service.base_dir = tmp_path

            with pytest.raises(ValueError, match="No default steps found"):
                service.get_default_steps_for_server("nonexistent")

    def test_reset_server_steps_with_post_invite_category(self, app, tmp_path):
        """Test resetting server steps with post_invite category (default)."""
        with app.app_context():
            # Clean up any existing steps first
            WizardStep.query.delete()
            db.session.commit()

            # Create existing custom steps
            custom_step1 = WizardStep(
                server_type="plex",
                category="post_invite",
                position=0,
                title="Custom Step 1",
                markdown="# Custom 1",
            )
            custom_step2 = WizardStep(
                server_type="plex",
                category="post_invite",
                position=1,
                title="Custom Step 2",
                markdown="# Custom 2",
            )
            db.session.add_all([custom_step1, custom_step2])
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

            service = WizardResetService()
            service.base_dir = tmp_path

            success, message, count = service.reset_server_steps("plex")

            assert success is True
            assert count == 2
            assert "deleted 2" in message
            assert "imported 2" in message

            # Verify custom steps were deleted and default steps imported
            plex_steps = (
                WizardStep.query.filter_by(server_type="plex", category="post_invite")
                .order_by(WizardStep.position)
                .all()
            )
            assert len(plex_steps) == 2
            assert plex_steps[0].title == "Welcome"
            assert plex_steps[0].category == "post_invite"
            assert plex_steps[1].title == "Setup"
            assert plex_steps[1].category == "post_invite"

    def test_reset_server_steps_with_pre_invite_category(self, app, tmp_path):
        """Test resetting server steps with pre_invite category."""
        with app.app_context():
            # Create existing custom pre-invite steps
            custom_step = WizardStep(
                server_type="jellyfin",
                category="pre_invite",
                position=0,
                title="Custom Pre Step",
                markdown="# Custom Pre",
            )
            db.session.add(custom_step)
            db.session.commit()

            # Create mock wizard steps directory
            jellyfin_dir = tmp_path / "jellyfin"
            jellyfin_dir.mkdir()
            (jellyfin_dir / "01-intro.md").write_text(
                """---
title: Introduction
---

# Welcome to Jellyfin
"""
            )

            service = WizardResetService()
            service.base_dir = tmp_path

            success, message, count = service.reset_server_steps(
                "jellyfin", category="pre_invite"
            )

            assert success is True
            assert count == 1
            assert "deleted 1" in message
            assert "imported 1" in message

            # Verify custom step was deleted and default step imported
            jellyfin_steps = WizardStep.query.filter_by(
                server_type="jellyfin", category="pre_invite"
            ).all()
            assert len(jellyfin_steps) == 1
            assert jellyfin_steps[0].title == "Introduction"
            assert jellyfin_steps[0].category == "pre_invite"

    def test_reset_only_affects_specified_category(self, app, tmp_path):
        """Test that resetting one category doesn't affect the other."""
        with app.app_context():
            # Clean up any existing steps first
            WizardStep.query.delete()
            db.session.commit()

            # Create steps in both categories
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

            service = WizardResetService()
            service.base_dir = tmp_path

            # Reset only post_invite category
            success, message, count = service.reset_server_steps(
                "plex", category="post_invite"
            )

            assert success is True

            # Verify pre_invite step is unchanged
            pre_steps = WizardStep.query.filter_by(
                server_type="plex", category="pre_invite"
            ).all()
            assert len(pre_steps) == 1
            assert pre_steps[0].title == "Pre Step"

            # Verify post_invite step was reset
            post_steps = WizardStep.query.filter_by(
                server_type="plex", category="post_invite"
            ).all()
            assert len(post_steps) == 1
            assert post_steps[0].title == "Welcome"

    def test_reset_server_steps_with_no_default_steps(self, app, tmp_path):
        """Test resetting when no default steps exist."""
        with app.app_context():
            # Create existing custom step
            custom_step = WizardStep(
                server_type="emby",
                category="post_invite",
                position=0,
                title="Custom Step",
                markdown="# Custom",
            )
            db.session.add(custom_step)
            db.session.commit()

            # Create empty directory (no markdown files)
            emby_dir = tmp_path / "emby"
            emby_dir.mkdir()

            service = WizardResetService()
            service.base_dir = tmp_path

            success, message, count = service.reset_server_steps("emby")

            assert success is False
            assert count == 0
            assert "No default steps found" in message

            # Verify custom step was NOT deleted (rollback occurred)
            emby_steps = WizardStep.query.filter_by(server_type="emby").all()
            assert len(emby_steps) == 1
            assert emby_steps[0].title == "Custom Step"

    def test_reset_server_steps_handles_database_error(self, app, tmp_path):
        """Test that database errors are handled gracefully."""
        with app.app_context():
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

            service = WizardResetService()
            service.base_dir = tmp_path

            # Mock db.session.commit to raise an exception
            with patch.object(db.session, "commit", side_effect=Exception("DB Error")):
                success, message, count = service.reset_server_steps("plex")

                assert success is False
                assert count == 0
                assert "Failed to reset steps" in message

    def test_reset_preserves_unique_constraint(self, app, tmp_path):
        """Test that reset respects unique constraint (server_type, category, position)."""
        with app.app_context():
            # Clean up any existing steps first
            WizardStep.query.delete()
            db.session.commit()

            # Create existing steps
            step1 = WizardStep(
                server_type="plex",
                category="post_invite",
                position=0,
                title="Step 1",
                markdown="# Step 1",
            )
            step2 = WizardStep(
                server_type="plex",
                category="post_invite",
                position=1,
                title="Step 2",
                markdown="# Step 2",
            )
            db.session.add_all([step1, step2])
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
            (plex_dir / "02-setup.md").write_text(
                """---
title: Setup
---

# Setup
"""
            )

            service = WizardResetService()
            service.base_dir = tmp_path

            success, message, count = service.reset_server_steps("plex")

            assert success is True

            # Verify no constraint violations occurred
            plex_steps = (
                WizardStep.query.filter_by(server_type="plex", category="post_invite")
                .order_by(WizardStep.position)
                .all()
            )
            assert len(plex_steps) == 2
            assert plex_steps[0].position == 0
            assert plex_steps[1].position == 1

    def test_reset_with_multiple_server_types(self, app, tmp_path):
        """Test that resetting one server type doesn't affect others."""
        with app.app_context():
            # Clean up any existing steps first
            WizardStep.query.delete()
            db.session.commit()

            # Create steps for multiple server types
            plex_step = WizardStep(
                server_type="plex",
                category="post_invite",
                position=0,
                title="Plex Step",
                markdown="# Plex",
            )
            jellyfin_step = WizardStep(
                server_type="jellyfin",
                category="post_invite",
                position=0,
                title="Jellyfin Step",
                markdown="# Jellyfin",
            )
            db.session.add_all([plex_step, jellyfin_step])
            db.session.commit()

            # Create mock wizard steps directory for plex only
            plex_dir = tmp_path / "plex"
            plex_dir.mkdir()
            (plex_dir / "01-welcome.md").write_text(
                """---
title: Welcome
---

# Welcome to Plex
"""
            )

            service = WizardResetService()
            service.base_dir = tmp_path

            # Reset only plex
            success, message, count = service.reset_server_steps("plex")

            assert success is True

            # Verify plex was reset
            plex_steps = WizardStep.query.filter_by(server_type="plex").all()
            assert len(plex_steps) == 1
            assert plex_steps[0].title == "Welcome"

            # Verify jellyfin was NOT affected
            jellyfin_steps = WizardStep.query.filter_by(server_type="jellyfin").all()
            assert len(jellyfin_steps) == 1
            assert jellyfin_steps[0].title == "Jellyfin Step"


class TestWizardResetRouteHandler:
    """Test the wizard_admin reset route handler."""

    def test_reset_route_resets_both_categories(
        self, app, authenticated_client, tmp_path
    ):
        """Test that the reset route handler resets BOTH pre_invite and post_invite categories.

        This is the key test that verifies the bug fix: the route handler should
        reset all steps for a server type, not just post_invite steps.
        """
        with app.app_context():
            # Clean up any existing steps first
            WizardStep.query.delete()
            db.session.commit()

            # Create custom steps in BOTH categories
            pre_step = WizardStep(
                server_type="plex",
                category="pre_invite",
                position=0,
                title="Custom Pre Step",
                markdown="# Custom Pre",
            )
            post_step = WizardStep(
                server_type="plex",
                category="post_invite",
                position=0,
                title="Custom Post Step",
                markdown="# Custom Post",
            )
            db.session.add_all([pre_step, post_step])
            db.session.commit()

            # Verify custom steps exist
            assert WizardStep.query.filter_by(server_type="plex").count() == 2

            # Create mock wizard steps directory with default steps
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

            # Mock the WizardResetService to use our tmp_path
            from app.services.wizard_reset import WizardResetService

            original_init = WizardResetService.__init__

            def mock_init(self):
                original_init(self)
                self.base_dir = tmp_path

            with patch.object(WizardResetService, "__init__", mock_init):
                # Call the route handler
                response = authenticated_client.post(
                    "/settings/wizard/reset/plex", follow_redirects=True
                )

                assert response.status_code == 200

            # Verify BOTH categories were reset
            # Pre-invite steps should be deleted (no defaults exist for pre_invite)
            pre_steps = WizardStep.query.filter_by(
                server_type="plex", category="pre_invite"
            ).all()
            assert len(pre_steps) == 0, "Pre-invite steps should be deleted"

            # Post-invite steps should be reset to defaults
            post_steps = (
                WizardStep.query.filter_by(server_type="plex", category="post_invite")
                .order_by(WizardStep.position)
                .all()
            )
            assert len(post_steps) == 2, "Post-invite steps should be reset to defaults"
            assert post_steps[0].title == "Welcome"
            assert post_steps[1].title == "Setup"

    def test_reset_route_with_only_post_invite_steps(
        self, app, authenticated_client, tmp_path
    ):
        """Test reset when only post_invite steps exist (backward compatibility)."""
        with app.app_context():
            # Clean up any existing steps first
            WizardStep.query.delete()
            db.session.commit()

            # Create only post_invite custom steps
            post_step = WizardStep(
                server_type="jellyfin",
                category="post_invite",
                position=0,
                title="Custom Post Step",
                markdown="# Custom Post",
            )
            db.session.add(post_step)
            db.session.commit()

            # Create mock wizard steps directory
            jellyfin_dir = tmp_path / "jellyfin"
            jellyfin_dir.mkdir()
            (jellyfin_dir / "01-intro.md").write_text(
                """---
title: Introduction
---

# Welcome to Jellyfin
"""
            )

            # Mock the WizardResetService to use our tmp_path
            from app.services.wizard_reset import WizardResetService

            original_init = WizardResetService.__init__

            def mock_init(self):
                original_init(self)
                self.base_dir = tmp_path

            with patch.object(WizardResetService, "__init__", mock_init):
                # Call the route handler
                response = authenticated_client.post(
                    "/settings/wizard/reset/jellyfin", follow_redirects=True
                )

                assert response.status_code == 200

            # Verify post_invite steps were reset
            post_steps = WizardStep.query.filter_by(
                server_type="jellyfin", category="post_invite"
            ).all()
            assert len(post_steps) == 1
            assert post_steps[0].title == "Introduction"

            # Verify no pre_invite steps exist
            pre_steps = WizardStep.query.filter_by(
                server_type="jellyfin", category="pre_invite"
            ).all()
            assert len(pre_steps) == 0
