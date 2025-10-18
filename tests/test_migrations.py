import os
import tempfile

import pytest
import requests
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


def _get_latest_release_migration():
    """Get the HEAD migration revision from the latest GitHub release."""
    try:
        # Get latest release info from GitHub API
        response = requests.get(
            "https://api.github.com/repos/wizarrrr/wizarr/releases/latest", timeout=10
        )
        response.raise_for_status()
        latest_tag = response.json()["tag_name"]

        # Map known releases to their HEAD migration revisions
        # This is based on the migration history at the time of release
        release_migrations = {
            "2025.8.2": "20250729_squashed_connections_expiry_system",
            "2025.8.3": "20250729_squashed_connections_expiry_system",  # 2025.8.3 uses same migrations as 2025.8.2
            "v2025.9.1": "39514b0aaad9",  # Latest release with admin column migration
            "v2025.9.2": "39514b0aaad9",  # Same migration state
            "v2025.9.3": "39514b0aaad9",  # Same migration state
            # Add future releases here as they are tagged
        }

        mapped_migration = release_migrations.get(latest_tag)
        if mapped_migration:
            return mapped_migration

        # For unmapped releases, try to use a reasonable fallback based on tag pattern
        # This provides more robustness for new releases that haven't been mapped yet
        if latest_tag.startswith("2025."):
            # Default to the most recent known stable migration
            return "20250729_squashed_connections_expiry_system"

        return None
    except Exception:
        # Fallback to a known stable release migration if API fails
        return "20250729_squashed_connections_expiry_system"


def _migrations_exist_after_release(release_migration):
    """Check if there are migrations newer than the release migration."""
    import glob
    import os

    # Get all migration files
    migrations_dir = os.path.join(os.path.dirname(__file__), "../migrations/versions")
    migration_files = glob.glob(os.path.join(migrations_dir, "*.py"))

    # Look for migrations that come after the release migration
    # This is a simple check - in practice you'd parse the migration chain
    newer_migrations = []

    for file in migration_files:
        filename = os.path.basename(file)
        if filename.startswith(("5252b5612761", "6fd264c262f1", "2a7f7c00c11f")):
            # These are migrations we know come after the 2025.8.2 release
            newer_migrations.append(filename)

    return len(newer_migrations) > 0


def test_upgrade_from_latest_release(migration_app, temp_db):
    """Test upgrading from the latest released version to current HEAD.

    This test simulates a real-world upgrade scenario where a user
    is upgrading from the latest released version to the current
    development version. It ensures migrations work properly in
    upgrade scenarios, not just fresh installs.
    """
    latest_release_migration = _get_latest_release_migration()

    if not latest_release_migration:
        pytest.skip("Could not determine latest release migration")

    # Note: We'll run the test even if there are no newer migrations
    # to ensure the migration infrastructure works properly

    with migration_app.app_context():
        # Step 1: Migrate to the latest release version state
        upgrade(revision=latest_release_migration)

        # Verify we're at the expected state (basic table check)
        engine = create_engine(temp_db)
        with engine.connect() as conn:
            # Check that core tables exist at this migration point
            result = conn.execute(
                text(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'alembic_%'"
                )
            )
            tables_at_release = {row[0] for row in result}

            # Core tables that should exist at any stable release
            required_release_tables = {"user", "invitation", "media_server", "library"}

            missing_core_tables = required_release_tables - tables_at_release
            assert not missing_core_tables, (
                f"Missing core tables at release {latest_release_migration}: {missing_core_tables}"
            )

        # Step 2: Upgrade from release version to current HEAD
        upgrade()  # Upgrade to HEAD (current development state)

        # Step 3: Verify the upgrade succeeded and all current tables exist
        with engine.connect() as conn:
            result = conn.execute(
                text(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'alembic_%'"
                )
            )
            tables_after_upgrade = {row[0] for row in result}

            # Expected tables in current HEAD state (should match full migration test)
            expected_current_tables = {
                "user",
                "invitation",
                "media_server",
                "library",
                "identity",
                "wizard_step",
                "wizard_bundle",
                "wizard_bundle_step",
                "invitation_server",
                "webauthn_credential",
                "admin_account",
            }

            missing_current_tables = expected_current_tables - tables_after_upgrade
            assert not missing_current_tables, (
                f"Missing tables after upgrade to HEAD: {missing_current_tables}"
            )

            # Verify no tables were lost during upgrade
            lost_tables = tables_at_release - tables_after_upgrade
            # Filter out tables that are legitimately removed/renamed during migrations
            expected_removals = set()  # Add any tables that should be removed
            unexpected_losses = lost_tables - expected_removals

            assert not unexpected_losses, (
                f"Tables unexpectedly lost during upgrade: {unexpected_losses}"
            )

            # Verify key constraints and indexes still work
            # (Test a few critical ones to ensure data integrity is maintained)

            # Check invitation table has basic required columns and new columns from migrations
            result = conn.execute(text("PRAGMA table_info(invitation)"))
            invitation_columns = {row[1] for row in result}

            # Basic required columns that should always exist
            required_core_columns = {
                "id",
                "code",
                "expires",  # Core invitation functionality
            }

            # New columns that should exist after upgrade (from migrations after release)
            expected_new_columns = {
                "wizard_bundle_id"  # From newer migrations after 2025.8.2
            }

            missing_core_columns = required_core_columns - invitation_columns
            assert not missing_core_columns, (
                f"Missing core columns in invitation table: {missing_core_columns}"
            )

            missing_new_columns = expected_new_columns - invitation_columns
            assert not missing_new_columns, (
                f"Missing new columns from upgrade in invitation table: {missing_new_columns}"
            )

            # Verify wizard_bundle_step unique constraint exists (from newer migrations)
            result = conn.execute(
                text(
                    "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='wizard_bundle_step' AND name LIKE 'sqlite_autoindex_%'"
                )
            )
            auto_indexes = [row[0] for row in result]
            has_unique_constraint = len(auto_indexes) > 0

            assert has_unique_constraint, (
                "wizard_bundle_step missing unique constraint after upgrade"
            )


def test_wizard_step_category_migration_upgrade(migration_app, temp_db):
    """Test that the category field migration adds column with correct default."""
    with migration_app.app_context():
        # Run migrations up to just before the category migration
        upgrade(revision="fd5a34530162")

        # Verify wizard_step table exists but doesn't have category column yet
        engine = create_engine(temp_db)
        with engine.connect() as conn:
            result = conn.execute(text("PRAGMA table_info(wizard_step)"))
            columns_before = {row[1] for row in result}
            assert "category" not in columns_before, (
                "category column should not exist before migration"
            )

            # Insert a test wizard step without category
            conn.execute(
                text(
                    """
                    INSERT INTO wizard_step
                        (server_type, position, title, markdown, created_at, updated_at)
                    VALUES
                        ('plex', 0, 'Test Step', '# Test', datetime('now'), datetime('now'))
                    """
                )
            )
            conn.commit()

        # Now run the category migration
        upgrade(revision="20251005_add_category_to_wizard_step")

        # Verify the migration succeeded
        with engine.connect() as conn:
            # Check category column was added
            result = conn.execute(text("PRAGMA table_info(wizard_step)"))
            columns_after = {row[1]: row for row in result}
            assert "category" in columns_after, "category column not added"

            # Verify default value is 'post_invite'
            category_col = columns_after["category"]
            assert category_col[4] == "'post_invite'", (
                f"category default should be 'post_invite', got {category_col[4]}"
            )

            # Verify existing step got default category
            result = conn.execute(
                text("SELECT category FROM wizard_step WHERE server_type = 'plex'")
            )
            row = result.fetchone()
            assert row is not None, "Test step not found"
            assert row[0] == "post_invite", (
                f"Existing step should have category 'post_invite', got {row[0]}"
            )

            # Verify new unique constraint exists
            result = conn.execute(
                text(
                    "SELECT sql FROM sqlite_master WHERE type='table' AND name='wizard_step'"
                )
            )
            table_sql = result.fetchone()[0]
            assert "uq_step_server_category_pos" in table_sql, (
                "New unique constraint not found"
            )
            assert "server_type, category, position" in table_sql, (
                "Unique constraint should include category"
            )


def test_wizard_step_category_migration_downgrade(migration_app, temp_db):
    """Test that the category field migration can be downgraded without data loss."""
    with migration_app.app_context():
        # Run migrations up to and including the category migration
        upgrade(revision="20251005_add_category_to_wizard_step")

        # Insert test data with both pre_invite and post_invite steps
        engine = create_engine(temp_db)
        with engine.connect() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO wizard_step
                        (server_type, category, position, title, markdown, created_at, updated_at)
                    VALUES
                        ('plex', 'pre_invite', 0, 'Pre Step', '# Pre', datetime('now'), datetime('now')),
                        ('plex', 'post_invite', 0, 'Post Step', '# Post', datetime('now'), datetime('now'))
                    """
                )
            )
            conn.commit()

            # Verify both steps exist
            result = conn.execute(text("SELECT COUNT(*) FROM wizard_step"))
            assert result.fetchone()[0] == 2, "Should have 2 test steps"

        # Now downgrade
        downgrade(revision="fd5a34530162")

        # Verify the downgrade succeeded
        with engine.connect() as conn:
            # Check category column was removed
            result = conn.execute(text("PRAGMA table_info(wizard_step)"))
            columns = {row[1] for row in result}
            assert "category" not in columns, "category column not removed"

            # Verify old unique constraint is restored
            result = conn.execute(
                text(
                    "SELECT sql FROM sqlite_master WHERE type='table' AND name='wizard_step'"
                )
            )
            table_sql = result.fetchone()[0]
            assert "uq_step_server_pos" in table_sql, (
                "Old unique constraint not restored"
            )
            assert "uq_step_server_category_pos" not in table_sql, (
                "New unique constraint should be removed"
            )

            # Verify post_invite step was preserved
            result = conn.execute(
                text("SELECT title FROM wizard_step WHERE server_type = 'plex'")
            )
            row = result.fetchone()
            assert row is not None, "Post-invite step should be preserved"
            assert row[0] == "Post Step", (
                f"Should preserve post_invite step, got {row[0]}"
            )

            # Verify only one step remains (pre_invite step should be dropped)
            result = conn.execute(text("SELECT COUNT(*) FROM wizard_step"))
            count = result.fetchone()[0]
            assert count == 1, (
                f"Should have 1 step after downgrade (post_invite only), got {count}"
            )


def test_wizard_step_category_unique_constraint(migration_app, temp_db):
    """Test that the unique constraint works correctly with category field."""
    with migration_app.app_context():
        # Run migrations up to and including the category migration
        upgrade(revision="20251005_add_category_to_wizard_step")

        engine = create_engine(temp_db)
        with engine.connect() as conn:
            # Test 1: Can insert steps with same position but different categories
            conn.execute(
                text(
                    """
                    INSERT INTO wizard_step
                        (server_type, category, position, title, markdown, created_at, updated_at)
                    VALUES
                        ('plex', 'pre_invite', 0, 'Pre Step 1', '# Pre', datetime('now'), datetime('now')),
                        ('plex', 'post_invite', 0, 'Post Step 1', '# Post', datetime('now'), datetime('now'))
                    """
                )
            )
            conn.commit()

            # Verify both steps were inserted
            result = conn.execute(
                text("SELECT COUNT(*) FROM wizard_step WHERE position = 0")
            )
            assert result.fetchone()[0] == 2, (
                "Should allow same position with different categories"
            )

            # Test 2: Cannot insert duplicate (server_type, category, position)
            try:
                conn.execute(
                    text(
                        """
                        INSERT INTO wizard_step
                            (server_type, category, position, title, markdown, created_at, updated_at)
                        VALUES
                            ('plex', 'pre_invite', 0, 'Duplicate', '# Dup', datetime('now'), datetime('now'))
                        """
                    )
                )
                conn.commit()
                raise AssertionError(
                    "Should not allow duplicate (server_type, category, position)"
                )
            except Exception as e:
                # Expected: unique constraint violation
                assert (
                    "UNIQUE constraint failed" in str(e) or "unique" in str(e).lower()
                ), f"Expected unique constraint error, got: {e}"
                conn.rollback()

            # Test 3: Can insert steps with same server_type and position but different categories
            conn.execute(
                text(
                    """
                    INSERT INTO wizard_step
                        (server_type, category, position, title, markdown, created_at, updated_at)
                    VALUES
                        ('jellyfin', 'pre_invite', 0, 'Jellyfin Pre', '# Pre', datetime('now'), datetime('now')),
                        ('jellyfin', 'post_invite', 0, 'Jellyfin Post', '# Post', datetime('now'), datetime('now'))
                    """
                )
            )
            conn.commit()

            # Verify all steps exist
            result = conn.execute(text("SELECT COUNT(*) FROM wizard_step"))
            assert result.fetchone()[0] == 4, "Should have 4 total steps"
