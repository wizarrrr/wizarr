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
    # Clean up any existing test database
    if os.path.exists(TestConfig._temp_db_path):
        os.unlink(TestConfig._temp_db_path)

    app = create_app(TestConfig)  # type: ignore[arg-type]
    with app.app_context():
        # Use Alembic migrations instead of db.create_all()
        # This ensures the test database schema matches production
        upgrade()
    yield app
    with app.app_context():
        db.drop_all()

    # Clean up test database file after session
    if os.path.exists(TestConfig._temp_db_path):
        os.unlink(TestConfig._temp_db_path)


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def runner(app):
    return app.test_cli_runner()
