from pathlib import Path

import pytest
from flask import Flask
from flask_login import LoginManager, UserMixin, login_user

from app.activity.api.blueprint import activity_bp


class _TestUser(UserMixin):
    id = "pytest-user"


@pytest.fixture
def activity_app():
    """Minimal Flask app with the activity blueprint registered."""
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY="testing-secret",
        TESTING=True,
    )

    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = "_login_route"

    @login_manager.user_loader
    def _load_user(user_id):  # pragma: no cover - required by flask-login
        if user_id == _TestUser.id:
            return _TestUser()
        return None

    @app.route("/_login")
    def _login_route():
        login_user(_TestUser())
        return "ok"

    template_dir = Path(__file__).resolve().parents[2] / "app" / "templates"
    if str(template_dir) not in app.jinja_loader.searchpath:
        app.jinja_loader.searchpath.append(str(template_dir))

    app.jinja_env.globals.setdefault("_", lambda s, **_: s)
    app.jinja_env.globals.setdefault(
        "ngettext",
        lambda singular, plural, number, **_: singular if number == 1 else plural,
    )

    app.register_blueprint(activity_bp)
    return app


@pytest.fixture
def activity_client(activity_app):
    return activity_app.test_client()


@pytest.fixture
def logged_activity_client(activity_client):
    activity_client.get("/_login")
    return activity_client
