"""Test the Jellyfin Max Active Sessions default on MediaServer create/edit."""

import pytest

from app import create_app
from app.config import BaseConfig
from app.extensions import db
from app.models import AdminAccount, MediaServer


class TestConfig(BaseConfig):
    TESTING = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"


@pytest.fixture
def app(monkeypatch):
    app = create_app(TestConfig)
    monkeypatch.setattr(
        "app.blueprints.media_servers.routes.check_jellyfin",
        lambda url, key: (True, ""),
    )
    with app.app_context():
        db.create_all()
        admin = AdminAccount(username="testadmin")
        admin.set_password("testpass")
        db.session.add(admin)
        db.session.commit()
    yield app
    with app.app_context():
        db.drop_all()


@pytest.fixture
def client(app):
    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess["_user_id"] = "admin"
        yield client


def test_create_server_stores_max_active_sessions(app, client):
    client.post(
        "/settings/servers/create",
        data={
            "server_name": "My Jellyfin",
            "server_type": "jellyfin",
            "server_url": "http://jellyfin.local",
            "api_key": "token",
            "max_active_sessions": "3",
        },
    )
    with app.app_context():
        server = MediaServer.query.filter_by(name="My Jellyfin").first()
        assert server.max_active_sessions == 3


def test_edit_server_updates_max_active_sessions(app, client):
    with app.app_context():
        server = MediaServer(
            name="My Jellyfin",
            server_type="jellyfin",
            url="http://jellyfin.local",
            api_key="token",
            max_active_sessions=3,
            verified=True,
        )
        db.session.add(server)
        db.session.commit()
        server_id = server.id

    client.post(
        f"/settings/servers/{server_id}/edit",
        data={
            "server_name": "My Jellyfin",
            "server_type": "jellyfin",
            "server_url": "http://jellyfin.local",
            "api_key": "token",
            "max_active_sessions": "0",
        },
    )
    with app.app_context():
        server = db.session.get(MediaServer, server_id)
        assert server.max_active_sessions == 0
