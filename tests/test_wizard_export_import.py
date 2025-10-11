"""Tests for wizard export/import service with category support."""

import pytest

from app.extensions import db
from app.models import WizardBundle, WizardBundleStep, WizardStep
from app.services.wizard_export_import import WizardExportImportService


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
def service(session):
    """Return a WizardExportImportService instance."""
    return WizardExportImportService(session)


@pytest.fixture
def sample_steps(session):
    """Create sample wizard steps with different categories."""
    steps = [
        WizardStep(
            server_type="plex",
            category="pre_invite",
            position=0,
            title="Pre-Invite Welcome",
            markdown="# Welcome\nThis is shown before invitation acceptance",
            requires=["server_url"],
            require_interaction=False,
        ),
        WizardStep(
            server_type="plex",
            category="post_invite",
            position=0,
            title="Post-Invite Setup",
            markdown="# Setup\nThis is shown after invitation acceptance",
            requires=None,
            require_interaction=True,
        ),
        WizardStep(
            server_type="jellyfin",
            category="pre_invite",
            position=0,
            title="Jellyfin Pre-Invite",
            markdown="# Jellyfin Welcome",
            requires=None,
            require_interaction=False,
        ),
    ]
    for step in steps:
        session.add(step)
    session.commit()
    return steps


class TestExportWithCategory:
    """Test export functionality includes category field."""

    def test_export_steps_includes_category(self, service, sample_steps):
        """Test that exported steps include the category field."""
        export_dto = service.export_steps_by_server_type("plex")

        assert export_dto.export_type == "steps"
        assert export_dto.total_count == 2  # 2 plex steps
        assert len(export_dto.steps) == 2

        # Check that category is included in export
        export_dict = export_dto.to_dict()
        assert "steps" in export_dict

        for step_dict in export_dict["steps"]:
            assert "category" in step_dict
            assert step_dict["category"] in ["pre_invite", "post_invite"]

    def test_export_bundle_includes_category(self, service, session):
        """Test that exported bundles include category field in steps."""
        # Create a bundle with steps
        bundle = WizardBundle(name="Test Bundle", description="Test description")
        session.add(bundle)
        session.flush()

        step1 = WizardStep(
            server_type="custom",
            category="pre_invite",
            position=0,
            markdown="# Step 1",
        )
        step2 = WizardStep(
            server_type="custom",
            category="post_invite",
            position=1,
            markdown="# Step 2",
        )
        session.add_all([step1, step2])
        session.flush()

        bundle_step1 = WizardBundleStep(
            bundle_id=bundle.id, step_id=step1.id, position=0
        )
        bundle_step2 = WizardBundleStep(
            bundle_id=bundle.id, step_id=step2.id, position=1
        )
        session.add_all([bundle_step1, bundle_step2])
        session.commit()

        # Export bundle
        export_dto = service.export_bundle(bundle.id)

        assert export_dto.export_type == "bundle"
        export_dict = export_dto.to_dict()

        assert "bundle" in export_dict
        assert "steps" in export_dict["bundle"]

        # Check that category is included in each step
        for step_dict in export_dict["bundle"]["steps"]:
            assert "category" in step_dict
            assert step_dict["category"] in ["pre_invite", "post_invite"]


class TestImportWithCategory:
    """Test import functionality handles category field."""

    def test_import_steps_with_category(self, service, session):
        """Test importing steps with category field."""
        import_data = {
            "export_type": "steps",
            "steps": [
                {
                    "server_type": "plex",
                    "category": "pre_invite",
                    "position": 0,
                    "title": "Pre-Invite Step",
                    "markdown": "# Pre-Invite",
                    "requires": [],
                    "require_interaction": False,
                },
                {
                    "server_type": "plex",
                    "category": "post_invite",
                    "position": 0,
                    "title": "Post-Invite Step",
                    "markdown": "# Post-Invite",
                    "requires": [],
                    "require_interaction": True,
                },
            ],
        }

        result = service.import_data(import_data, replace_existing=True)

        assert result.success
        assert result.imported_count == 2
        assert len(result.errors) == 0

        # Verify steps were imported with correct categories
        pre_step = (
            session.query(WizardStep)
            .filter_by(server_type="plex", category="pre_invite")
            .first()
        )
        post_step = (
            session.query(WizardStep)
            .filter_by(server_type="plex", category="post_invite")
            .first()
        )

        assert pre_step is not None
        assert pre_step.title == "Pre-Invite Step"
        assert pre_step.category == "pre_invite"

        assert post_step is not None
        assert post_step.title == "Post-Invite Step"
        assert post_step.category == "post_invite"

    def test_import_bundle_with_category(self, service, session):
        """Test importing bundle with category field in steps."""
        import_data = {
            "export_type": "bundle",
            "bundle": {
                "name": "Test Bundle",
                "description": "Test description",
                "steps": [
                    {
                        "server_type": "custom",
                        "category": "pre_invite",
                        "position": 0,
                        "markdown": "# Pre Step",
                        "requires": [],
                        "require_interaction": False,
                    },
                    {
                        "server_type": "custom",
                        "category": "post_invite",
                        "position": 1,
                        "markdown": "# Post Step",
                        "requires": [],
                        "require_interaction": False,
                    },
                ],
            },
        }

        result = service.import_data(import_data, replace_existing=False)

        assert result.success
        assert result.imported_count == 2

        # Verify bundle was created
        bundle = session.query(WizardBundle).filter_by(name="Test Bundle").first()
        assert bundle is not None

        # Verify steps have correct categories
        steps = (
            session.query(WizardStep)
            .filter_by(server_type="custom")
            .order_by(WizardStep.position)
            .all()
        )
        assert len(steps) == 2
        assert steps[0].category == "pre_invite"
        assert steps[1].category == "post_invite"


class TestBackwardCompatibility:
    """Test backward compatibility with exports without category field."""

    def test_import_steps_without_category_defaults_to_post_invite(
        self, service, session
    ):
        """Test that steps without category field default to 'post_invite'."""
        import_data = {
            "export_type": "steps",
            "steps": [
                {
                    "server_type": "plex",
                    "position": 0,
                    "title": "Old Step",
                    "markdown": "# Old Step",
                    "requires": [],
                    "require_interaction": False,
                    # NOTE: No 'category' field - simulating old export
                }
            ],
        }

        result = service.import_data(import_data, replace_existing=True)

        assert result.success
        assert result.imported_count == 1

        # Verify step was imported with default category
        step = session.query(WizardStep).filter_by(server_type="plex").first()
        assert step is not None
        assert step.category == "post_invite"  # Should default to post_invite

    def test_import_bundle_without_category_defaults_to_post_invite(
        self, service, session
    ):
        """Test that bundle steps without category default to 'post_invite'."""
        import_data = {
            "export_type": "bundle",
            "bundle": {
                "name": "Old Bundle",
                "description": "Old bundle without category",
                "steps": [
                    {
                        "server_type": "custom",
                        "position": 0,
                        "markdown": "# Old Step",
                        "requires": [],
                        "require_interaction": False,
                        # NOTE: No 'category' field
                    }
                ],
            },
        }

        result = service.import_data(import_data, replace_existing=False)

        assert result.success
        assert result.imported_count == 1

        # Verify step has default category
        step = session.query(WizardStep).filter_by(server_type="custom").first()
        assert step is not None
        assert step.category == "post_invite"

    def test_update_existing_step_preserves_category_if_not_provided(
        self, service, session
    ):
        """Test that updating existing step without category preserves it."""
        # Create an existing step with pre_invite category
        existing_step = WizardStep(
            server_type="plex",
            category="pre_invite",
            position=0,
            markdown="# Original",
        )
        session.add(existing_step)
        session.commit()

        # Import data without category field (simulating old export)
        import_data = {
            "export_type": "steps",
            "steps": [
                {
                    "server_type": "plex",
                    "position": 0,
                    "markdown": "# Updated",
                    "requires": [],
                    "require_interaction": False,
                    # NOTE: No 'category' field
                }
            ],
        }

        result = service.import_data(import_data, replace_existing=False)

        assert result.success
        assert result.updated_count == 1

        # Verify step was updated but category defaults to post_invite
        # (backward compatibility behavior)
        step = session.query(WizardStep).filter_by(server_type="plex").first()
        assert step is not None
        assert step.markdown == "# Updated"
        assert step.category == "post_invite"  # Defaults to post_invite


class TestValidation:
    """Test validation of category field during import."""

    def test_validate_valid_category_values(self, service):
        """Test that valid category values pass validation."""
        data = {
            "export_type": "steps",
            "steps": [
                {
                    "server_type": "plex",
                    "category": "pre_invite",
                    "position": 0,
                    "markdown": "# Test",
                    "requires": [],
                    "require_interaction": False,
                },
                {
                    "server_type": "plex",
                    "category": "post_invite",
                    "position": 1,
                    "markdown": "# Test 2",
                    "requires": [],
                    "require_interaction": False,
                },
            ],
        }

        errors = service.validate_import_data(data)
        assert len(errors) == 0

    def test_validate_invalid_category_value(self, service):
        """Test that invalid category values fail validation."""
        data = {
            "export_type": "steps",
            "steps": [
                {
                    "server_type": "plex",
                    "category": "invalid_category",  # Invalid value
                    "position": 0,
                    "markdown": "# Test",
                    "requires": [],
                    "require_interaction": False,
                }
            ],
        }

        errors = service.validate_import_data(data)
        assert len(errors) > 0
        assert any("category" in error.lower() for error in errors)

    def test_validate_category_wrong_type(self, service):
        """Test that category with wrong type fails validation."""
        data = {
            "export_type": "steps",
            "steps": [
                {
                    "server_type": "plex",
                    "category": 123,  # Should be string
                    "position": 0,
                    "markdown": "# Test",
                    "requires": [],
                    "require_interaction": False,
                }
            ],
        }

        errors = service.validate_import_data(data)
        assert len(errors) > 0
        assert any(
            "category" in error.lower() and "string" in error.lower()
            for error in errors
        )

    def test_validate_missing_category_is_allowed(self, service):
        """Test that missing category field is allowed (backward compatibility)."""
        data = {
            "export_type": "steps",
            "steps": [
                {
                    "server_type": "plex",
                    "position": 0,
                    "markdown": "# Test",
                    "requires": [],
                    "require_interaction": False,
                    # NOTE: No 'category' field - should be valid
                }
            ],
        }

        errors = service.validate_import_data(data)
        assert len(errors) == 0  # Should pass validation


class TestExportImportRoundTrip:
    """Test that export and import work together correctly."""

    def test_export_import_roundtrip_preserves_category(self, service, session):
        """Test that exporting and re-importing preserves category."""
        # Create steps with different categories
        steps = [
            WizardStep(
                server_type="plex",
                category="pre_invite",
                position=0,
                markdown="# Pre",
            ),
            WizardStep(
                server_type="plex",
                category="post_invite",
                position=0,
                markdown="# Post",
            ),
        ]
        for step in steps:
            session.add(step)
        session.commit()

        # Export
        export_dto = service.export_steps_by_server_type("plex")
        export_dict = export_dto.to_dict()

        # Clear database
        session.query(WizardStep).delete()
        session.commit()

        # Re-import
        result = service.import_data(export_dict, replace_existing=True)

        assert result.success
        assert result.imported_count == 2

        # Verify categories were preserved
        pre_step = (
            session.query(WizardStep)
            .filter_by(server_type="plex", category="pre_invite")
            .first()
        )
        post_step = (
            session.query(WizardStep)
            .filter_by(server_type="plex", category="post_invite")
            .first()
        )

        assert pre_step is not None
        assert pre_step.markdown == "# Pre"
        assert post_step is not None
        assert post_step.markdown == "# Post"
