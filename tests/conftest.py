import atexit
import contextlib
import logging
import os
import shutil
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


# Each test process gets its own directory for the database. Then test runs
# in parallel (for example in two git worktrees) do not share one SQLite file.
_TEST_DB_DIR = tempfile.mkdtemp(prefix="wizarr-tests-")
atexit.register(shutil.rmtree, _TEST_DB_DIR, ignore_errors=True)


class TestConfig(BaseConfig):
    TESTING = True
    WTF_CSRF_ENABLED = False
    # Use a temporary file database for better migration compatibility
    _temp_db_path = os.path.join(_TEST_DB_DIR, "wizarr_test.db")
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{_temp_db_path}"


@pytest.fixture(scope="session")
def app():
    # Clean up any existing test database files (including WAL files)
    for ext in ["", "-wal", "-shm"]:
        db_file = TestConfig._temp_db_path + ext
        if os.path.exists(db_file):
            with contextlib.suppress(Exception):
                os.unlink(db_file)

    app = create_app(TestConfig)  # type: ignore
    with app.app_context():
        # Use the Alembic migrations, not db.create_all(), so that the test
        # schema is the same as in production.
        _upgrade()
    yield app
    with app.app_context():
        db.drop_all()

    # Clean up test database files after session (including WAL files)
    for ext in ["", "-wal", "-shm"]:
        db_file = TestConfig._temp_db_path + ext
        if os.path.exists(db_file):
            with contextlib.suppress(Exception):
                os.unlink(db_file)


# The loggers that were enabled before the first migration run. The
# fileConfig() call in migrations/env.py disables all loggers that exist, each
# time a test runs migrations. Production runs `flask db upgrade` in a
# separate process, so this does not occur there.
_ENABLED_LOGGERS: list[logging.Logger] = []


def _enable_loggers():
    for logger in _ENABLED_LOGGERS:
        logger.disabled = False


def _upgrade():
    """Run the migrations, then undo their side effects on this process."""
    _ENABLED_LOGGERS[:] = [
        logger
        for logger in logging.Logger.manager.loggerDict.values()
        if isinstance(logger, logging.Logger) and not logger.disabled
    ]
    upgrade()
    _enable_loggers()
    # Some migrations set PRAGMA foreign_keys=OFF on the pooled connection.
    # Close it, so that each new connection gets foreign_keys=ON.
    db.engine.dispose()


@pytest.fixture
def client(app):
    return app.test_client()


def _delete_test_data():
    """Delete all test rows, children before parents (foreign keys)."""
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

    db.session.rollback()
    db.session.execute(db.text("DELETE FROM activity_snapshot"))
    db.session.execute(db.text("DELETE FROM password_reset_token"))
    db.session.execute(db.text("DELETE FROM historical_import_job"))
    db.session.query(ActivitySession).delete()
    db.session.query(ExpiredUser).delete()
    db.session.execute(db.text("DELETE FROM wizard_bundle_step"))
    db.session.execute(db.text("DELETE FROM wizard_bundle"))
    db.session.execute(db.text("DELETE FROM invitation_server"))
    db.session.execute(db.text("DELETE FROM invitation_user"))
    db.session.execute(db.text("DELETE FROM invite_library"))
    db.session.query(WizardStep).delete()
    db.session.query(Invitation).delete()
    db.session.query(User).delete()
    db.session.execute(db.text("DELETE FROM identity"))
    db.session.query(Library).delete()
    db.session.query(MediaServer).delete()
    db.session.query(WebAuthnCredential).delete()
    db.session.query(ApiKey).delete()
    db.session.query(AdminAccount).delete()
    db.session.query(Settings).delete()
    db.session.commit()


@pytest.fixture
def session(app):
    """Provide a database session that starts and ends with empty tables."""
    with app.app_context():
        _delete_test_data()
        yield db.session
        _delete_test_data()


@pytest.fixture
def admin_user(session):
    """An admin account (username "testadmin", password "TestPass123")."""
    from app.models import AdminAccount

    admin = AdminAccount(username="testadmin")
    admin.set_password("TestPass123")
    session.add(admin)
    session.commit()
    return admin


@pytest.fixture
def admin_client(client, admin_user):
    """A test client with a logged-in admin session."""
    with client.session_transaction() as sess:
        sess["_user_id"] = str(admin_user.id)
        sess["_fresh"] = True
    return client


@pytest.fixture
def clear_media_caches():
    """Clear the class-level image proxy and Plex caches before and after a test."""
    from app.services.image_proxy import ImageProxyService
    from app.services.media.plex import clear_plex_connection_cache

    def clear():
        ImageProxyService._token_cache.clear()
        ImageProxyService._image_cache.clear()
        ImageProxyService._total_image_bytes = 0
        ImageProxyService._cipher_key_cache.clear()
        ImageProxyService._server_url_cache.clear()
        ImageProxyService._server_header_cache.clear()
        ImageProxyService._session_cache.clear()
        clear_plex_connection_cache()

    clear()
    yield
    clear()


@pytest.fixture(autouse=True)
def _keep_loggers_enabled():
    """Enable the loggers again after a test that runs migrations."""
    yield
    _enable_loggers()


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
