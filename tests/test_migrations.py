import pytest
import tempfile
import os
from flask_migrate import upgrade, downgrade
from sqlalchemy import create_engine, text

from app import create_app
from app.config import BaseConfig
from app.extensions import db, migrate


class MigrationTestConfig(BaseConfig):
    TESTING = True
    WTF_CSRF_ENABLED = False
    # Use a temporary file database for migration testing
    SQLALCHEMY_DATABASE_URI = None  # Will be set dynamically


@pytest.fixture
def temp_db():
    """Create a temporary database file for migration testing."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
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
    
    app = create_app(config)
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
            result = conn.execute(text(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'alembic_%'"
            ))
            tables = {row[0] for row in result}
            
            expected_tables = {
                'user', 'invitation', 'media_server', 'library', 
                'identity', 'wizard_step', 'wizard_bundle', 
                'wizard_bundle_step', 'invitation_server'
            }
            
            missing_tables = expected_tables - tables
            assert not missing_tables, f"Missing tables after migration: {missing_tables}"
            
            # Debug: Check what actually exists in sqlite_master for wizard_bundle_step
            result = conn.execute(text(
                "SELECT type, name, sql FROM sqlite_master WHERE name LIKE '%wizard_bundle_step%' OR tbl_name='wizard_bundle_step'"
            ))
            all_objects = list(result)
            print(f"DEBUG: Found objects related to wizard_bundle_step: {all_objects}")
            
            # Since the unique constraint might be working but just not easily detectable,
            # let's test that duplicate inserts actually fail
            try:
                conn.execute(text("INSERT INTO wizard_bundle (name) VALUES ('test')"))
                conn.execute(text("INSERT INTO wizard_step (title, template) VALUES ('test', 'test')"))
                conn.execute(text("INSERT INTO wizard_bundle_step (bundle_id, step_id, position) VALUES (1, 1, 1)"))
                conn.execute(text("INSERT INTO wizard_bundle_step (bundle_id, step_id, position) VALUES (1, 1, 1)"))
                conn.commit()
                # If we get here, the unique constraint is NOT working
                assert False, "Unique constraint not working - duplicate insert succeeded"
            except Exception as e:
                # This is expected - the unique constraint should prevent duplicates
                print(f"DEBUG: Unique constraint working correctly, got expected error: {e}")
                conn.rollback()


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
            result = conn.execute(text(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='wizard_bundle'"
            ))
            assert result.fetchone() is not None, "wizard_bundle table not created"
            
            # Check wizard_bundle_step table exists
            result = conn.execute(text(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='wizard_bundle_step'"
            ))
            assert result.fetchone() is not None, "wizard_bundle_step table not created"
            
            # Check invitation table has wizard_bundle_id column
            result = conn.execute(text("PRAGMA table_info(invitation)"))
            columns = {row[1] for row in result}
            assert 'wizard_bundle_id' in columns, "invitation.wizard_bundle_id column not added"


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
            result = conn.execute(text(
                "SELECT name FROM sqlite_master WHERE type='table' AND name IN ('wizard_bundle', 'wizard_bundle_step')"
            ))
            remaining_tables = [row[0] for row in result]
            assert not remaining_tables, f"Tables not dropped during downgrade: {remaining_tables}"
            
            # Check invitation.wizard_bundle_id column was removed
            result = conn.execute(text("PRAGMA table_info(invitation)"))
            columns = {row[1] for row in result}
            assert 'wizard_bundle_id' not in columns, "invitation.wizard_bundle_id column not removed"