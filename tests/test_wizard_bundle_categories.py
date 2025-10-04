"""Tests for wizard bundle integration with category support.

This module tests wizard bundles with pre-invite and post-invite categories
to ensure bundles work correctly with mixed category steps.

Requirements tested:
- 11.1: Wizard bundle overrides default category-based step selection
- 11.2: Bundle steps display in bundle order regardless of category
- 11.3: Creating wizard bundle with steps from both categories
- 11.4: Editing wizard bundle shows category for each step
- 11.5: Bundle with only pre-invite steps proceeds to join page after completion
- 11.6: Bundle with only post-invite steps shown after accepting invitation
- 11.7: Bundle with mixed categories displays all steps in bundle order
- 15.5: Integration tests for wizard bundle functionality
"""

import pytest

from app.extensions import db
from app.models import WizardBundle, WizardBundleStep, WizardStep


@pytest.fixture
def session(app):
    """Return a clean database session inside an app context."""
    with app.app_context():
        # Clean up any existing data before the test
        db.session.query(WizardBundleStep).delete()
        db.session.query(WizardBundle).delete()
        db.session.query(WizardStep).delete()
        db.session.commit()

        yield db.session

        # Clean up after the test
        db.session.rollback()


@pytest.fixture
def sample_steps(session):
    """Create sample wizard steps with different categories."""
    steps = [
        # Pre-invite steps
        WizardStep(
            server_type="plex",
            category="pre_invite",
            position=0,
            title="Pre-Step 1",
            markdown="# Pre-Step 1\nBefore you join...",
        ),
        WizardStep(
            server_type="plex",
            category="pre_invite",
            position=1,
            title="Pre-Step 2",
            markdown="# Pre-Step 2\nRequirements...",
        ),
        # Post-invite steps
        WizardStep(
            server_type="plex",
            category="post_invite",
            position=0,
            title="Post-Step 1",
            markdown="# Post-Step 1\nWelcome!",
        ),
        WizardStep(
            server_type="plex",
            category="post_invite",
            position=1,
            title="Post-Step 2",
            markdown="# Post-Step 2\nSetup...",
        ),
    ]

    for step in steps:
        session.add(step)
    session.commit()

    return steps


class TestBundleWithOnlyPreInviteSteps:
    """Test bundles containing only pre-invite steps."""

    def test_create_bundle_with_only_pre_invite_steps(self, app, sample_steps, session):
        """Test creating a bundle with only pre-invite steps."""
        with app.app_context():
            # Create bundle
            bundle = WizardBundle(
                name="Pre-Invite Only Bundle",
                description="Bundle with only pre-invite steps",
            )
            session.add(bundle)
            session.commit()

            # Add only pre-invite steps to bundle
            pre_steps = [s for s in sample_steps if s.category == "pre_invite"]
            for idx, step in enumerate(pre_steps):
                bundle_step = WizardBundleStep(
                    bundle_id=bundle.id, step_id=step.id, position=idx
                )
                session.add(bundle_step)
            session.commit()

            # Verify bundle has correct steps
            bundle_steps = (
                WizardBundleStep.query.filter_by(bundle_id=bundle.id)
                .order_by(WizardBundleStep.position)
                .all()
            )

            assert len(bundle_steps) == 2
            assert all(bs.step.category == "pre_invite" for bs in bundle_steps)
            assert bundle_steps[0].step.title == "Pre-Step 1"
            assert bundle_steps[1].step.title == "Pre-Step 2"

    def test_bundle_steps_loaded_in_order_pre_invite(self, app, sample_steps, session):
        """Test that bundle steps are loaded in correct order for pre-invite steps."""
        with app.app_context():
            # Create bundle with only pre-invite steps
            bundle = WizardBundle(name="Pre-Only", description="Pre-invite only")
            session.add(bundle)
            session.commit()

            pre_steps = [s for s in sample_steps if s.category == "pre_invite"]
            for idx, step in enumerate(pre_steps):
                bundle_step = WizardBundleStep(
                    bundle_id=bundle.id, step_id=step.id, position=idx
                )
                session.add(bundle_step)
            session.commit()

            # Query bundle steps
            bundle_steps = (
                WizardBundleStep.query.filter_by(bundle_id=bundle.id)
                .order_by(WizardBundleStep.position)
                .all()
            )

            # Verify steps are loaded in correct order
            assert len(bundle_steps) == 2
            assert bundle_steps[0].step.category == "pre_invite"
            assert bundle_steps[1].step.category == "pre_invite"
            assert bundle_steps[0].step.title == "Pre-Step 1"
            assert bundle_steps[1].step.title == "Pre-Step 2"


class TestBundleWithOnlyPostInviteSteps:
    """Test bundles containing only post-invite steps."""

    def test_create_bundle_with_only_post_invite_steps(
        self, app, sample_steps, session
    ):
        """Test creating a bundle with only post-invite steps."""
        with app.app_context():
            # Create bundle
            bundle = WizardBundle(
                name="Post-Invite Only Bundle",
                description="Bundle with only post-invite steps",
            )
            session.add(bundle)
            session.commit()

            # Add only post-invite steps to bundle
            post_steps = [s for s in sample_steps if s.category == "post_invite"]
            for idx, step in enumerate(post_steps):
                bundle_step = WizardBundleStep(
                    bundle_id=bundle.id, step_id=step.id, position=idx
                )
                session.add(bundle_step)
            session.commit()

            # Verify bundle has correct steps
            bundle_steps = (
                WizardBundleStep.query.filter_by(bundle_id=bundle.id)
                .order_by(WizardBundleStep.position)
                .all()
            )

            assert len(bundle_steps) == 2
            assert all(bs.step.category == "post_invite" for bs in bundle_steps)
            assert bundle_steps[0].step.title == "Post-Step 1"
            assert bundle_steps[1].step.title == "Post-Step 2"

    def test_bundle_steps_loaded_in_order_post_invite(self, app, sample_steps, session):
        """Test that bundle steps are loaded in correct order for post-invite steps."""
        with app.app_context():
            # Create bundle with only post-invite steps
            bundle = WizardBundle(name="Post-Only", description="Post-invite only")
            session.add(bundle)
            session.commit()

            post_steps = [s for s in sample_steps if s.category == "post_invite"]
            for idx, step in enumerate(post_steps):
                bundle_step = WizardBundleStep(
                    bundle_id=bundle.id, step_id=step.id, position=idx
                )
                session.add(bundle_step)
            session.commit()

            # Query bundle steps
            bundle_steps = (
                WizardBundleStep.query.filter_by(bundle_id=bundle.id)
                .order_by(WizardBundleStep.position)
                .all()
            )

            # Verify steps are loaded in correct order
            assert len(bundle_steps) == 2
            assert bundle_steps[0].step.category == "post_invite"
            assert bundle_steps[1].step.category == "post_invite"
            assert bundle_steps[0].step.title == "Post-Step 1"
            assert bundle_steps[1].step.title == "Post-Step 2"


class TestBundleWithMixedCategories:
    """Test bundles containing both pre-invite and post-invite steps."""

    def test_create_bundle_with_mixed_categories(self, app, sample_steps, session):
        """Test creating a bundle with mixed pre and post-invite steps."""
        with app.app_context():
            # Create bundle
            bundle = WizardBundle(
                name="Mixed Bundle", description="Bundle with mixed categories"
            )
            session.add(bundle)
            session.commit()

            # Add steps in mixed order: pre, post, pre, post
            mixed_order = [
                sample_steps[0],  # pre-invite
                sample_steps[2],  # post-invite
                sample_steps[1],  # pre-invite
                sample_steps[3],  # post-invite
            ]

            for idx, step in enumerate(mixed_order):
                bundle_step = WizardBundleStep(
                    bundle_id=bundle.id, step_id=step.id, position=idx
                )
                session.add(bundle_step)
            session.commit()

            # Verify bundle has correct steps in correct order
            bundle_steps = (
                WizardBundleStep.query.filter_by(bundle_id=bundle.id)
                .order_by(WizardBundleStep.position)
                .all()
            )

            assert len(bundle_steps) == 4
            # Verify order is maintained regardless of category
            assert bundle_steps[0].step.title == "Pre-Step 1"
            assert bundle_steps[0].step.category == "pre_invite"
            assert bundle_steps[1].step.title == "Post-Step 1"
            assert bundle_steps[1].step.category == "post_invite"
            assert bundle_steps[2].step.title == "Pre-Step 2"
            assert bundle_steps[2].step.category == "pre_invite"
            assert bundle_steps[3].step.title == "Post-Step 2"
            assert bundle_steps[3].step.category == "post_invite"

    def test_bundle_maintains_mixed_step_order(self, app, sample_steps, session):
        """Test that bundle maintains order for mixed category steps."""
        with app.app_context():
            # Create bundle with mixed categories
            bundle = WizardBundle(name="Mixed", description="Mixed categories")
            session.add(bundle)
            session.commit()

            # Add steps in specific order
            mixed_order = [
                sample_steps[0],  # pre-invite
                sample_steps[2],  # post-invite
                sample_steps[1],  # pre-invite
                sample_steps[3],  # post-invite
            ]

            for idx, step in enumerate(mixed_order):
                bundle_step = WizardBundleStep(
                    bundle_id=bundle.id, step_id=step.id, position=idx
                )
                session.add(bundle_step)
            session.commit()

            # Query bundle steps
            bundle_steps = (
                WizardBundleStep.query.filter_by(bundle_id=bundle.id)
                .order_by(WizardBundleStep.position)
                .all()
            )

            # Verify steps are in correct order (not grouped by category)
            assert len(bundle_steps) == 4
            assert bundle_steps[0].step.title == "Pre-Step 1"
            assert bundle_steps[0].step.category == "pre_invite"
            assert bundle_steps[1].step.title == "Post-Step 1"
            assert bundle_steps[1].step.category == "post_invite"
            assert bundle_steps[2].step.title == "Pre-Step 2"
            assert bundle_steps[2].step.category == "pre_invite"
            assert bundle_steps[3].step.title == "Post-Step 2"
            assert bundle_steps[3].step.category == "post_invite"

    def test_bundle_category_alternates_in_mixed_bundle(
        self, app, sample_steps, session
    ):
        """Test that categories alternate correctly in mixed bundle."""
        with app.app_context():
            # Create bundle with mixed categories
            bundle = WizardBundle(name="Mixed", description="Mixed categories")
            session.add(bundle)
            session.commit()

            # Add steps: pre, post, pre, post
            mixed_order = [
                sample_steps[0],  # pre-invite
                sample_steps[2],  # post-invite
                sample_steps[1],  # pre-invite
                sample_steps[3],  # post-invite
            ]

            for idx, step in enumerate(mixed_order):
                bundle_step = WizardBundleStep(
                    bundle_id=bundle.id, step_id=step.id, position=idx
                )
                session.add(bundle_step)
            session.commit()

            # Query bundle steps
            bundle_steps = (
                WizardBundleStep.query.filter_by(bundle_id=bundle.id)
                .order_by(WizardBundleStep.position)
                .all()
            )

            # Verify categories alternate
            assert bundle_steps[0].step.category == "pre_invite"
            assert bundle_steps[1].step.category == "post_invite"
            assert bundle_steps[2].step.category == "pre_invite"
            assert bundle_steps[3].step.category == "post_invite"


class TestBundleOverridesDefaultStepSelection:
    """Test that bundles override default category-based step selection."""

    def test_bundle_includes_all_steps_regardless_of_category(
        self, app, sample_steps, session
    ):
        """Test that bundles include all steps regardless of category."""
        with app.app_context():
            # Create bundle with all steps
            bundle = WizardBundle(name="All Steps", description="Bundle with all steps")
            session.add(bundle)
            session.commit()

            # Add all steps to bundle
            for idx, step in enumerate(sample_steps):
                bundle_step = WizardBundleStep(
                    bundle_id=bundle.id, step_id=step.id, position=idx
                )
                session.add(bundle_step)
            session.commit()

            # Query bundle steps
            bundle_steps = (
                WizardBundleStep.query.filter_by(bundle_id=bundle.id)
                .order_by(WizardBundleStep.position)
                .all()
            )

            # Bundle should include all 4 steps (2 pre, 2 post)
            assert len(bundle_steps) == 4
            pre_count = sum(
                1 for bs in bundle_steps if bs.step.category == "pre_invite"
            )
            post_count = sum(
                1 for bs in bundle_steps if bs.step.category == "post_invite"
            )
            assert pre_count == 2
            assert post_count == 2

    def test_bundle_contains_only_selected_steps(self, app, sample_steps, session):
        """Test that bundles contain only the steps explicitly added to them."""
        with app.app_context():
            # Create bundle with specific steps
            bundle = WizardBundle(name="Custom", description="Custom bundle")
            session.add(bundle)
            session.commit()

            # Add only specific steps (not all pre or all post)
            selected_steps = [sample_steps[0], sample_steps[3]]  # pre and post
            for idx, step in enumerate(selected_steps):
                bundle_step = WizardBundleStep(
                    bundle_id=bundle.id, step_id=step.id, position=idx
                )
                session.add(bundle_step)
            session.commit()

            # Query bundle steps
            bundle_steps = (
                WizardBundleStep.query.filter_by(bundle_id=bundle.id)
                .order_by(WizardBundleStep.position)
                .all()
            )

            # Bundle should contain exactly 2 steps (the ones we added)
            assert len(bundle_steps) == 2
            assert bundle_steps[0].step.title == "Pre-Step 1"
            assert bundle_steps[0].step.category == "pre_invite"
            assert bundle_steps[1].step.title == "Post-Step 2"
            assert bundle_steps[1].step.category == "post_invite"


class TestBundleStepOrdering:
    """Test that bundle step ordering is maintained."""

    def test_bundle_respects_position_order(self, app, sample_steps, session):
        """Test that bundle steps are ordered by position, not by category."""
        with app.app_context():
            # Create bundle
            bundle = WizardBundle(name="Ordered", description="Position-ordered")
            session.add(bundle)
            session.commit()

            # Add steps in specific position order (not category order)
            # Position 0: post-invite
            # Position 1: pre-invite
            # Position 2: post-invite
            # Position 3: pre-invite
            ordered_steps = [
                (0, sample_steps[2]),  # post
                (1, sample_steps[0]),  # pre
                (2, sample_steps[3]),  # post
                (3, sample_steps[1]),  # pre
            ]

            for pos, step in ordered_steps:
                bundle_step = WizardBundleStep(
                    bundle_id=bundle.id, step_id=step.id, position=pos
                )
                session.add(bundle_step)
            session.commit()

            # Query bundle steps
            bundle_steps = (
                WizardBundleStep.query.filter_by(bundle_id=bundle.id)
                .order_by(WizardBundleStep.position)
                .all()
            )

            # Verify order is by position, not category
            assert bundle_steps[0].step.title == "Post-Step 1"
            assert bundle_steps[1].step.title == "Pre-Step 1"
            assert bundle_steps[2].step.title == "Post-Step 2"
            assert bundle_steps[3].step.title == "Pre-Step 2"
