"""Tests for the short Settings cache of the context processor and middleware."""

from flask import Flask

from app.context_processors import inject_server_name
from app.extensions import db
from app.middleware import require_onboarding
from app.models import Settings
from app.settings_cache import clear_settings_cache, get_cached_setting


def _set(key, value):
    setting = Settings.query.filter_by(key=key).first()
    if setting is None:
        setting = Settings(key=key)
        db.session.add(setting)
    setting.value = value
    db.session.commit()


def test_server_name_is_cached(app, session):
    with app.app_context():
        _set("server_name", "First")
        assert inject_server_name() == {"server_name": "First"}

        # A change that does not commit through the ORM is not visible
        # until the cache expires.
        db.session.execute(
            db.text("UPDATE settings SET value = 'Hidden' WHERE key = 'server_name'")
        )
        db.session.commit()
        assert inject_server_name() == {"server_name": "First"}
        clear_settings_cache()
        assert inject_server_name() == {"server_name": "Hidden"}


def test_server_name_change_clears_the_cache(app, session):
    with app.app_context():
        _set("server_name", "First")
        assert inject_server_name() == {"server_name": "First"}

        _set("server_name", "Second")
        assert inject_server_name() == {"server_name": "Second"}


def test_bulk_delete_clears_the_cache(app, session):
    with app.app_context():
        _set("server_name", "First")
        assert inject_server_name() == {"server_name": "First"}

        Settings.query.filter_by(key="server_name").delete()
        db.session.commit()
        assert inject_server_name() == {"server_name": "Wizarr"}


def test_cache_expires(app, session, monkeypatch):
    clock = [1000.0]
    monkeypatch.setattr("app.settings_cache.time.monotonic", lambda: clock[0])
    calls = []

    def loader():
        calls.append(1)
        return "value"

    with app.app_context():
        get_cached_setting("ttl-test", loader)
        get_cached_setting("ttl-test", loader)
        assert len(calls) == 1

        clock[0] += 31
        get_cached_setting("ttl-test", loader)
        assert len(calls) == 2


def test_onboarding_check_sees_a_new_admin_at_once(app, session):
    # The middleware skips the check in TESTING mode, so use a second app
    # without TESTING that shares the database configuration.
    check_app = Flask("onboarding-check")
    check_app.config.update(
        SQLALCHEMY_DATABASE_URI=app.config["SQLALCHEMY_DATABASE_URI"],
    )
    db.init_app(check_app)

    @check_app.route("/setup/", endpoint="setup.onboarding")
    def onboarding():  # pragma: no cover - only the URL is needed
        return "setup"

    with check_app.test_request_context("/admin"):
        _set("admin_username", "")
        response = require_onboarding()
        assert response is not None
        assert response.status_code == 302

        # No admin is not cached, so the next request sees the new admin.
        _set("admin_username", "admin")
        assert require_onboarding() is None

    with check_app.app_context():
        db.engine.dispose()
