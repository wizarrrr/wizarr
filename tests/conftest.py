import contextlib
import os
import tempfile

import pytest
from flask_migrate import upgrade

from app import create_app
from app.config import BaseConfig
from app.extensions import db

# Workaround for Python 3.13 macOS proxy detection bug
# https://github.com/python/cpython/issues/112509
os.environ["NO_PROXY"] = "*"
os.environ["no_proxy"] = "*"


class TestConfig(BaseConfig):
    TESTING = True
    WTF_CSRF_ENABLED = False
    # Use a temporary file database for better migration compatibility
    _temp_db_path = os.path.join(tempfile.gettempdir(), "wizarr_test.db")
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{_temp_db_path}"


class E2ETestConfig(BaseConfig):
    TESTING = True
    WTF_CSRF_ENABLED = False
    # Use a temporary file database that both test process and live server can access
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{tempfile.gettempdir()}/wizarr_e2e_test.db"


@pytest.fixture(scope="session")
def app():
    # Clean up any existing test database files (including WAL files)
    for ext in ["", "-wal", "-shm"]:
        db_file = TestConfig._temp_db_path + ext
        if os.path.exists(db_file):
            with contextlib.suppress(Exception):
                os.unlink(db_file)

    app = create_app(TestConfig)  # type: ignore[arg-type]
    with app.app_context():
        # Use Alembic migrations instead of db.create_all()
        # This ensures the test database schema matches production
        upgrade()
    yield app
    with app.app_context():
        db.drop_all()

    # Clean up test database files after session (including WAL files)
    for ext in ["", "-wal", "-shm"]:
        db_file = TestConfig._temp_db_path + ext
        if os.path.exists(db_file):
            with contextlib.suppress(Exception):
                os.unlink(db_file)


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def runner(app):
    return app.test_cli_runner()


@pytest.fixture
def session(app):
    """Provide a clean database session for tests that explicitly request it.

    This fixture ensures test isolation by cleaning up all test data
    before and after the test runs.
    """
    from app.models import (
        ActivitySession,
        AdminAccount,
        ApiKey,
        ExpiredUser,
        Invitation,
        Library,
        MediaServer,
        Settings,
        User,
        WebAuthnCredential,
        WizardStep,
    )

    with app.app_context():
        # Clean up before the test to ensure fresh state
        db.session.rollback()
        # Delete all test data in correct order (respecting foreign keys)
        # Plus tables first
        db.session.execute(db.text("DELETE FROM activity_snapshot"))
        db.session.execute(db.text("DELETE FROM historical_import_job"))
        db.session.query(ActivitySession).delete()
        db.session.query(ExpiredUser).delete()
        # Junction tables
        db.session.execute(db.text("DELETE FROM wizard_bundle_step"))
        db.session.execute(db.text("DELETE FROM wizard_bundle"))
        db.session.execute(db.text("DELETE FROM invitation_server"))
        db.session.execute(db.text("DELETE FROM invitation_user"))
        # Main tables
        db.session.query(WizardStep).delete()
        db.session.query(Invitation).delete()
        db.session.query(User).delete()
        db.session.query(Library).delete()
        db.session.query(MediaServer).delete()
        # Tables with FK to AdminAccount - delete before AdminAccount
        db.session.query(WebAuthnCredential).delete()
        db.session.query(ApiKey).delete()
        # Now safe to delete AdminAccount
        db.session.query(AdminAccount).delete()
        db.session.query(Settings).delete()
        db.session.commit()

        yield db.session

        # Clean up after the test
        db.session.rollback()
        # Delete all test data in correct order (respecting foreign keys)
        # Plus tables first
        db.session.execute(db.text("DELETE FROM activity_snapshot"))
        db.session.execute(db.text("DELETE FROM historical_import_job"))
        db.session.query(ActivitySession).delete()
        db.session.query(ExpiredUser).delete()
        # Junction tables
        db.session.execute(db.text("DELETE FROM wizard_bundle_step"))
        db.session.execute(db.text("DELETE FROM wizard_bundle"))
        db.session.execute(db.text("DELETE FROM invitation_server"))
        db.session.execute(db.text("DELETE FROM invitation_user"))
        # Main tables
        db.session.query(WizardStep).delete()
        db.session.query(Invitation).delete()
        db.session.query(User).delete()
        db.session.query(Library).delete()
        db.session.query(MediaServer).delete()
        # Tables with FK to AdminAccount - delete before AdminAccount
        db.session.query(WebAuthnCredential).delete()
        db.session.query(ApiKey).delete()
        # Now safe to delete AdminAccount
        db.session.query(AdminAccount).delete()
        db.session.query(Settings).delete()
        db.session.commit()


@pytest.fixture(autouse=True)
def cleanup_redirect_loop_data(app):
    """Automatically clean up data that causes redirect loops between tests.

    This minimal cleanup runs for all tests to prevent redirect loops while
    preserving data that other fixtures may need.
    """
    from app.models import Settings

    # No cleanup before the test - let fixtures set up their data
    yield

    # After the test, remove only the admin_username setting to prevent
    # redirect loops in subsequent tests
    try:
        with app.app_context():
            db.session.rollback()
            # Only delete the specific setting that causes redirect loops
            admin_setting = Settings.query.filter_by(key="admin_username").first()
            if admin_setting:
                db.session.delete(admin_setting)
                db.session.commit()
    except Exception:
        # Silently ignore cleanup errors (e.g., if app context is not available)
        pass
