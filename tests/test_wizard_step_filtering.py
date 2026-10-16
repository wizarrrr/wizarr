"""Tests for wizard step filtering by category.

This module tests the _steps() function in app/blueprints/wizard/routes.py
to ensure proper filtering by category (pre_invite vs post_invite).
"""

import pytest

from app.blueprints.wizard.routes import _steps
from app.models import WizardStep


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

    session.add_all(steps)
    session.commit()

    return steps


class TestStepsFilteringByCategory:
    """Test filtering wizard steps by category."""

    @pytest.mark.parametrize(
        ("server_type", "kwargs", "expected"),
        [
            ("plex", {"category": "pre_invite"}, ["Pre-Welcome", "Requirements"]),
            (
                "plex",
                {"category": "post_invite"},
                ["Welcome to Plex!", "Let's get started"],
            ),
            # Without a category, _steps() returns the post_invite steps.
            ("plex", {}, ["Welcome to Plex!", "Let's get started"]),
            ("jellyfin", {"category": "pre_invite"}, ["Before you join Jellyfin"]),
            ("jellyfin", {"category": "post_invite"}, ["Welcome to Jellyfin!"]),
        ],
        ids=["plex-pre", "plex-post", "plex-default", "jellyfin-pre", "jellyfin-post"],
    )
    def test_filter_by_server_type_and_category(
        self, sample_steps, server_type, kwargs, expected
    ):
        steps = _steps(server_type, {}, **kwargs)

        assert len(steps) == len(expected)
        for step, text in zip(steps, expected, strict=True):
            assert text in step.content

    def test_no_steps_for_category(self, session):
        """Test behavior when no steps exist for a category."""
        session.add(
            WizardStep(
                server_type="emby",
                category="post_invite",
                position=0,
                markdown="# Welcome",
            )
        )
        session.commit()

        assert _steps("emby", {}, category="pre_invite") == []
        assert len(_steps("emby", {}, category="post_invite")) == 1

    def test_steps_ordered_by_position(self, session):
        """Test that steps are returned in correct position order."""
        for pos, title in [(2, "Third"), (0, "First"), (1, "Second")]:
            session.add(
                WizardStep(
                    server_type="plex",
                    category="pre_invite",
                    position=pos,
                    title=title,
                    markdown=f"# {title}",
                )
            )
        session.commit()

        steps = _steps("plex", {}, category="pre_invite")

        assert [s.content for s in steps] == ["# First", "# Second", "# Third"]


class TestLegacyMarkdownFileFallback:
    """Test fallback to legacy markdown files."""

    def test_legacy_files_treated_as_post_invite(self, session):
        """Test that legacy markdown files are treated as post_invite only."""
        # Legacy files do not support pre_invite.
        assert _steps("plex", {}, category="pre_invite") == []

        # Without DB steps, post_invite falls back to the files in wizard_steps/plex.
        assert len(_steps("plex", {}, category="post_invite")) > 0

    def test_db_steps_override_legacy_files(self, session):
        """Test that DB steps take precedence over legacy markdown files."""
        session.add(
            WizardStep(
                server_type="plex",
                category="post_invite",
                position=0,
                markdown="# DB Step",
            )
        )
        session.commit()

        steps = _steps("plex", {}, category="post_invite")

        assert len(steps) == 1
        assert steps[0].content == "# DB Step"


def test_row_adapter_matches_frontmatter_post_api(session):
    """_RowAdapter has the .content and .get() API of frontmatter.Post."""
    session.add_all(
        [
            WizardStep(
                server_type="plex",
                category="pre_invite",
                position=0,
                markdown="# Needs a click",
                require_interaction=True,
            ),
            WizardStep(
                server_type="plex",
                category="pre_invite",
                position=1,
                markdown="# Plain",
            ),
        ]
    )
    session.commit()

    gated, plain = _steps("plex", {}, category="pre_invite")

    assert gated.content == "# Needs a click"
    assert gated.get("require", False) is True
    assert plain.get("require", False) is False
    assert plain.get("unknown_key", "default") == "default"
    assert plain.get("unknown_key") is None
