import pytest
from flask_migrate import downgrade, upgrade
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError

from app import create_app
from app.config import BaseConfig
from app.models import WizardBundle, WizardBundleStep, WizardStep


class MigrationTestConfig(BaseConfig):
    TESTING = True
    WTF_CSRF_ENABLED = False
    # Use a temporary file database for migration testing
    SQLALCHEMY_DATABASE_URI = None  # Will be set dynamically


@pytest.fixture
def temp_db(tmp_path):
    """Return the URL of a new, empty SQLite database file."""
    return f"sqlite:///{tmp_path / 'migrations.db'}"


@pytest.fixture
def migration_app(temp_db):
    """Create app with temporary database for migration testing."""
    config = MigrationTestConfig()
    config.SQLALCHEMY_DATABASE_URI = temp_db

    app = create_app(config)  # type: ignore
    yield app


def test_migrated_schema_rejects_duplicate_bundle_position(session):
    """The conftest app runs all migrations. Two steps cannot share a bundle position."""
    bundle = WizardBundle(name="Bundle")
    first = WizardStep(server_type="plex", position=0, markdown="# First")
    second = WizardStep(server_type="plex", position=1, markdown="# Second")
    session.add_all([bundle, first, second])
    session.flush()
    session.add_all(
        [
            WizardBundleStep(bundle_id=bundle.id, step_id=first.id, position=0),
            WizardBundleStep(bundle_id=bundle.id, step_id=second.id, position=0),
        ]
    )

    with pytest.raises(IntegrityError):
        session.flush()
    session.rollback()


def test_expired_user_event_migration_repairs_existing_data(migration_app, temp_db):
    """Test duplicate removal, disabled-state repair, and the unique index."""
    with migration_app.app_context():
        upgrade(revision="20260401_repair")

        engine = create_engine(temp_db)
        with engine.connect() as connection:
            expiry_time = "2026-08-01 00:00:00.000000"
            connection.execute(
                text("""
                    INSERT INTO "user"
                        (id, token, username, email, code, expires, is_disabled,
                         is_ldap_user)
                    VALUES
                        (42, 'token', 'expired-user', 'expired@example.com',
                         'EXPIRED', :expiry_time, 0, 0)
                """),
                {"expiry_time": expiry_time},
            )
            connection.execute(
                text("""
                    INSERT INTO expired_user
                        (original_user_id, username, expired_at, deleted_at)
                    VALUES
                        (42, 'expired-user', :expiry_time, :expiry_time),
                        (42, 'expired-user', :expiry_time, :expiry_time)
                """),
                {"expiry_time": expiry_time},
            )
            connection.commit()

        upgrade(revision="20260901_expired_unique")

        with engine.connect() as connection:
            event_count = connection.execute(
                text("SELECT COUNT(*) FROM expired_user")
            ).scalar_one()
            disabled = connection.execute(
                text('SELECT is_disabled FROM "user" WHERE id = 42')
            ).scalar_one()
            indexes = {
                row[1]
                for row in connection.execute(text("PRAGMA index_list(expired_user)"))
            }

            assert event_count == 1
            assert disabled == 1
            assert "uq_expired_user_event" in indexes

            with pytest.raises(IntegrityError):
                connection.execute(
                    text("""
                        INSERT INTO expired_user
                            (original_user_id, username, expired_at, deleted_at)
                        VALUES
                            (42, 'expired-user', :expiry_time, :expiry_time)
                    """),
                    {"expiry_time": expiry_time},
                )


def test_migration_downgrade(migration_app, temp_db):
    """The wizard bundle migration can be downgraded."""
    bundle_tables_sql = text(
        "SELECT name FROM sqlite_master WHERE type='table' "
        "AND name IN ('wizard_bundle', 'wizard_bundle_step')"
    )
    with migration_app.app_context():
        upgrade(revision="20250703_add_wizard_bundle_tables")

        engine = create_engine(temp_db)
        with engine.connect() as conn:
            tables = {row[0] for row in conn.execute(bundle_tables_sql)}
            assert tables == {"wizard_bundle", "wizard_bundle_step"}
            columns = {
                row[1] for row in conn.execute(text("PRAGMA table_info(invitation)"))
            }
            assert "wizard_bundle_id" in columns

        downgrade(revision="20250702_add_jellyfin_options")

        with engine.connect() as conn:
            remaining_tables = [row[0] for row in conn.execute(bundle_tables_sql)]
            assert not remaining_tables, (
                f"Tables not dropped during downgrade: {remaining_tables}"
            )

            result = conn.execute(text("PRAGMA table_info(invitation)"))
            columns = {row[1] for row in result}
            assert "wizard_bundle_id" not in columns, (
                "invitation.wizard_bundle_id column not removed"
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
            row = result.fetchone()
            assert row is not None
            table_sql = row[0]
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
            row = result.fetchone()
            assert row is not None
            assert row[0] == 2, "Should have 2 test steps"

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
            row = result.fetchone()
            assert row is not None
            table_sql = row[0]
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
            row = result.fetchone()
            assert row is not None
            count = row[0]
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
            row = result.fetchone()
            assert row is not None
            assert row[0] == 2, "Should allow same position with different categories"

            # Test 2: Cannot insert duplicate (server_type, category, position)
            with pytest.raises(IntegrityError, match="UNIQUE constraint failed"):
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
            row = result.fetchone()
            assert row is not None
            assert row[0] == 4, "Should have 4 total steps"
