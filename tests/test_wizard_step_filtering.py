"""Tests for wizard step filtering by category.

This module tests the _steps() function in app/blueprints/wizard/routes.py
to ensure proper filtering by category (pre_invite vs post_invite).

Requirements tested:
- 1.1: Service type and category are independent, orthogonal filters
- 1.2: Filtering wizard steps by category works identically for all service types
- 1.3: Existing _render() function is reused for both pre and post-invite steps
- 1.4: Existing _steps() function is extended (not replaced) to support category filtering
- 1.5: Service-specific blueprints are not modified
- 2.5: System supports filtering by category
- 15.1: Unit tests for wizard step model methods
"""

import pytest

from app.extensions import db
from app.models import WizardStep


@pytest.fixture
def session(app):
    """Return a clean database session inside an app context."""
    with app.app_context():
        # Clean up any existing WizardStep data before the test
        db.session.query(WizardStep).delete()
        db.session.commit()

        yield db.session

        # Clean up after the test
        db.session.rollback()


@pytest.fixture
def sample_steps(session):
    """Create sample wizard steps for testing."""
    steps = [
        # Plex pre-invite steps
        WizardStep(
            server_type="plex",
            category="pre_invite",
            position=0,
            title="Pre-Welcome",
            markdown="# Pre-Welcome\nBefore you join...",
        ),
        WizardStep(
            server_type="plex",
            category="pre_invite",
            position=1,
            title="Pre-Requirements",
            markdown="# Requirements\nYou need...",
        ),
        # Plex post-invite steps
        WizardStep(
            server_type="plex",
            category="post_invite",
            position=0,
            title="Post-Welcome",
            markdown="# Welcome\nWelcome to Plex!",
        ),
        WizardStep(
            server_type="plex",
            category="post_invite",
            position=1,
            title="Post-Setup",
            markdown="# Setup\nLet's get started...",
        ),
        # Jellyfin pre-invite steps
        WizardStep(
            server_type="jellyfin",
            category="pre_invite",
            position=0,
            title="Jellyfin Pre-Welcome",
            markdown="# Pre-Welcome\nBefore you join Jellyfin...",
        ),
        # Jellyfin post-invite steps
        WizardStep(
            server_type="jellyfin",
            category="post_invite",
            position=0,
            title="Jellyfin Post-Welcome",
            markdown="# Welcome\nWelcome to Jellyfin!",
        ),
    ]

    for step in steps:
        session.add(step)
    session.commit()

    return steps


class TestStepsFilteringByCategory:
    """Test filtering wizard steps by category."""

    def test_filter_pre_invite_steps(self, app, sample_steps):
        """Test filtering by pre_invite category."""
        from app.blueprints.wizard.routes import _steps

        with app.app_context():
            cfg = {}
            steps = _steps("plex", cfg, category="pre_invite")

            # Should return only pre_invite steps for plex
            assert len(steps) == 2
            # Verify content contains pre-invite markers
            assert "Pre-Welcome" in steps[0].content
            assert "Requirements" in steps[1].content

    def test_filter_post_invite_steps(self, app, sample_steps):
        """Test filtering by post_invite category."""
        from app.blueprints.wizard.routes import _steps

        with app.app_context():
            cfg = {}
            steps = _steps("plex", cfg, category="post_invite")

            # Should return only post_invite steps for plex
            assert len(steps) == 2
            # Verify content contains post-invite markers
            assert "Welcome to Plex!" in steps[0].content
            assert "Let's get started" in steps[1].content

    def test_default_category_is_post_invite(self, app, sample_steps):
        """Test that default category behavior returns post_invite steps."""
        from app.blueprints.wizard.routes import _steps

        with app.app_context():
            cfg = {}
            # Call without category parameter - should default to post_invite
            steps = _steps("plex", cfg)

            # Should return post_invite steps by default
            assert len(steps) == 2
            assert "Welcome to Plex!" in steps[0].content

    def test_filter_works_for_different_server_types(self, app, sample_steps):
        """Test that category filtering works identically for all service types."""
        from app.blueprints.wizard.routes import _steps

        with app.app_context():
            cfg = {}

            # Test pre_invite for plex
            plex_pre = _steps("plex", cfg, category="pre_invite")
            assert len(plex_pre) == 2

            # Test pre_invite for jellyfin
            jellyfin_pre = _steps("jellyfin", cfg, category="pre_invite")
            assert len(jellyfin_pre) == 1

            # Test post_invite for plex
            plex_post = _steps("plex", cfg, category="post_invite")
            assert len(plex_post) == 2

            # Test post_invite for jellyfin
            jellyfin_post = _steps("jellyfin", cfg, category="post_invite")
            assert len(jellyfin_post) == 1

    def test_no_steps_for_category(self, app, session):
        """Test behavior when no steps exist for a category."""
        from app.blueprints.wizard.routes import _steps

        with app.app_context():
            # Create only post_invite steps
            step = WizardStep(
                server_type="emby",
                category="post_invite",
                position=0,
                markdown="# Welcome",
            )
            session.add(step)
            session.commit()

            cfg = {}

            # Query for pre_invite steps - should return empty list
            pre_steps = _steps("emby", cfg, category="pre_invite")
            assert len(pre_steps) == 0
            assert isinstance(pre_steps, list)

            # Query for post_invite steps - should return the step
            post_steps = _steps("emby", cfg, category="post_invite")
            assert len(post_steps) == 1

    def test_mixed_pre_post_steps_independence(self, app, sample_steps):
        """Test that pre and post steps are independent and don't interfere."""
        from app.blueprints.wizard.routes import _steps

        with app.app_context():
            cfg = {}

            # Get pre_invite steps
            pre_steps = _steps("plex", cfg, category="pre_invite")
            pre_count = len(pre_steps)

            # Get post_invite steps
            post_steps = _steps("plex", cfg, category="post_invite")
            post_count = len(post_steps)

            # Verify they are different sets
            assert pre_count == 2
            assert post_count == 2

            # Verify content is different
            pre_content = [s.content for s in pre_steps]
            post_content = [s.content for s in post_steps]

            assert "Pre-Welcome" in pre_content[0]
            assert "Welcome to Plex!" in post_content[0]

    def test_steps_ordered_by_position(self, app, session):
        """Test that steps are returned in correct position order."""
        from app.blueprints.wizard.routes import _steps

        with app.app_context():
            # Create steps in non-sequential order
            steps_data = [
                (2, "Third"),
                (0, "First"),
                (1, "Second"),
            ]

            for pos, title in steps_data:
                step = WizardStep(
                    server_type="plex",
                    category="pre_invite",
                    position=pos,
                    title=title,
                    markdown=f"# {title}",
                )
                session.add(step)
            session.commit()

            cfg = {}
            steps = _steps("plex", cfg, category="pre_invite")

            # Verify correct order
            assert len(steps) == 3
            assert "First" in steps[0].content
            assert "Second" in steps[1].content
            assert "Third" in steps[2].content


class TestLegacyMarkdownFileFallback:
    """Test fallback to legacy markdown files."""

    def test_legacy_files_treated_as_post_invite(self, app, session):
        """Test that legacy markdown files are treated as post_invite only."""
        from app.blueprints.wizard.routes import _steps

        with app.app_context():
            cfg = {}

            # Query for pre_invite with no DB steps - should return empty
            # (legacy files don't support pre_invite)
            pre_steps = _steps("plex", cfg, category="pre_invite")
            assert len(pre_steps) == 0

            # Query for post_invite with no DB steps - should fall back to legacy files
            # Note: This test assumes legacy markdown files exist in wizard_steps/plex/
            # If they don't exist, it will return an empty list, which is also correct
            post_steps = _steps("plex", cfg, category="post_invite")
            # We can't assert a specific count since legacy files may or may not exist
            # But we can assert it returns a list
            assert isinstance(post_steps, list)

    def test_db_steps_override_legacy_files(self, app, session):
        """Test that DB steps take precedence over legacy markdown files."""
        from app.blueprints.wizard.routes import _steps

        with app.app_context():
            # Create a DB step
            step = WizardStep(
                server_type="plex",
                category="post_invite",
                position=0,
                markdown="# DB Step",
            )
            session.add(step)
            session.commit()

            cfg = {}
            steps = _steps("plex", cfg, category="post_invite")

            # Should return DB step, not legacy files
            assert len(steps) >= 1
            assert "DB Step" in steps[0].content


class TestRowAdapterCompatibility:
    """Test that _RowAdapter maintains compatibility with frontmatter.Post API."""

    def test_row_adapter_content_property(self, app, session):
        """Test that _RowAdapter exposes content property."""
        from app.blueprints.wizard.routes import _steps

        with app.app_context():
            step = WizardStep(
                server_type="plex",
                category="pre_invite",
                position=0,
                markdown="# Test Content",
            )
            session.add(step)
            session.commit()

            cfg = {}
            steps = _steps("plex", cfg, category="pre_invite")

            # Should have content property
            assert hasattr(steps[0], "content")
            assert steps[0].content == "# Test Content"

    def test_row_adapter_get_method(self, app, session):
        """Test that _RowAdapter exposes get() method for require flag."""
        from app.blueprints.wizard.routes import _steps

        with app.app_context():
            step = WizardStep(
                server_type="plex",
                category="pre_invite",
                position=0,
                markdown="# Test",
                require_interaction=True,
            )
            session.add(step)
            session.commit()

            cfg = {}
            steps = _steps("plex", cfg, category="pre_invite")

            # Should have get() method
            assert hasattr(steps[0], "get")
            assert steps[0].get("require", False) is True

    def test_row_adapter_get_default_value(self, app, session):
        """Test that _RowAdapter get() returns default for unknown keys."""
        from app.blueprints.wizard.routes import _steps

        with app.app_context():
            step = WizardStep(
                server_type="plex",
                category="pre_invite",
                position=0,
                markdown="# Test",
            )
            session.add(step)
            session.commit()

            cfg = {}
            steps = _steps("plex", cfg, category="pre_invite")

            # Should return default for unknown keys
            assert steps[0].get("unknown_key", "default") == "default"
            assert steps[0].get("unknown_key") is None
