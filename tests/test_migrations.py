import os
import tempfile

import pytest
from flask_migrate import downgrade, upgrade
from sqlalchemy import create_engine, text

from app import create_app
from app.config import BaseConfig


class MigrationTestConfig(BaseConfig):
    TESTING = True
    WTF_CSRF_ENABLED = False
    # Use a temporary file database for migration testing
    SQLALCHEMY_DATABASE_URI = None  # Will be set dynamically


@pytest.fixture
def temp_db():
    """Create a temporary database file for migration testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    try:
        yield f"sqlite:///{db_path}"
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


@pytest.fixture
def migration_app(temp_db):
    """Create app with temporary database for migration testing."""
    config = MigrationTestConfig()
    config.SQLALCHEMY_DATABASE_URI = temp_db

    app = create_app(config)  # type: ignore[arg-type]
    yield app


def test_full_migration_upgrade(migration_app, temp_db):
    """Test that all migrations can be applied from scratch."""
    with migration_app.app_context():
        # Run all migrations from the beginning
        upgrade()

        # Verify that key tables exist after migration
        engine = create_engine(temp_db)
        with engine.connect() as conn:
            # Check that main tables exist
            result = conn.execute(
                text(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'alembic_%'"
                )
            )
            tables = {row[0] for row in result}

            expected_tables = {
                "user",
                "invitation",
                "media_server",
                "library",
                "identity",
                "wizard_step",
                "wizard_bundle",
                "wizard_bundle_step",
                "invitation_server",
            }

            missing_tables = expected_tables - tables
            assert not missing_tables, (
                f"Missing tables after migration: {missing_tables}"
            )

            # Verify wizard_bundle_step has the unique constraint
            # Check for SQLite auto-generated unique index (appears as sqlite_autoindex_*)
            result = conn.execute(
                text(
                    "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='wizard_bundle_step' AND name LIKE 'sqlite_autoindex_%'"
                )
            )
            auto_indexes = [row[0] for row in result]
            has_unique_constraint = len(auto_indexes) > 0

            assert has_unique_constraint, (
                "wizard_bundle_step missing unique constraint (no sqlite_autoindex found)"
            )


def test_problematic_migration_specifically(migration_app, temp_db):
    """Test the specific migration that was causing issues in production."""
    with migration_app.app_context():
        # Run migrations up to just before the problematic one
        upgrade(revision="20250702_add_jellyfin_options")

        # Now run the problematic migration
        upgrade(revision="20250703_add_wizard_bundle_tables")

        # Verify the migration succeeded
        engine = create_engine(temp_db)
        with engine.connect() as conn:
            # Check wizard_bundle table exists
            result = conn.execute(
                text(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='wizard_bundle'"
                )
            )
            assert result.fetchone() is not None, "wizard_bundle table not created"

            # Check wizard_bundle_step table exists
            result = conn.execute(
                text(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='wizard_bundle_step'"
                )
            )
            assert result.fetchone() is not None, "wizard_bundle_step table not created"

            # Check invitation table has wizard_bundle_id column
            result = conn.execute(text("PRAGMA table_info(invitation)"))
            columns = {row[1] for row in result}
            assert "wizard_bundle_id" in columns, (
                "invitation.wizard_bundle_id column not added"
            )


def test_migration_downgrade(migration_app, temp_db):
    """Test that the problematic migration can be downgraded."""
    with migration_app.app_context():
        # Run migrations up to and including the problematic one
        upgrade(revision="20250703_add_wizard_bundle_tables")

        # Now downgrade
        downgrade(revision="20250702_add_jellyfin_options")

        # Verify the downgrade succeeded
        engine = create_engine(temp_db)
        with engine.connect() as conn:
            # Check tables were dropped
            result = conn.execute(
                text(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name IN ('wizard_bundle', 'wizard_bundle_step')"
                )
            )
            remaining_tables = [row[0] for row in result]
            assert not remaining_tables, (
                f"Tables not dropped during downgrade: {remaining_tables}"
            )

            # Check invitation.wizard_bundle_id column was removed
            result = conn.execute(text("PRAGMA table_info(invitation)"))
            columns = {row[1] for row in result}
            assert "wizard_bundle_id" not in columns, (
                "invitation.wizard_bundle_id column not removed"
            )
