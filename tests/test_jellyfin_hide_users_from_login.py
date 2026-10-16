"""
A Jellyfin server option hides or shows new users on the login screens (#1225).

Jellyfin hides new users by default (UserPolicy.IsHidden = true), and Wizarr
copied that policy back. The option defaults to True, so existing servers
keep that behaviour. Emby has other flags, so Wizarr keeps the Emby defaults.
"""

import re
from unittest.mock import patch

import pytest
from flask_migrate import downgrade, upgrade
from sqlalchemy import create_engine, text

from app import create_app
from app.config import BaseConfig
from app.extensions import db
from app.models import (
    Invitation,
    MediaServer,
    User,
    invitation_servers,
)
from app.services.media.jellyfin import JellyfinClient, login_screen_policy

REVISION = "20261011_hide_users_from_login"


class _Response:
    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


def _server(server_type="jellyfin", **kwargs):
    server = MediaServer(
        name=f"{server_type} server",
        server_type=server_type,
        url=f"http://{server_type}.local",
        api_key="key",
        **kwargs,
    )
    db.session.add(server)
    db.session.commit()
    return server


class _CapturingJellyfin(JellyfinClient):
    """A Jellyfin client that keeps the policy instead of sending it."""

    def __init__(self, server: MediaServer) -> None:
        self._attach_server_row(server)
        self.policy_updates: list[dict] = []

    def create_user(self, username: str, password: str) -> str:
        return "jf-user-1"

    def _set_specific_folders(self, user_id: str, names: list[str]) -> None:
        return None

    def get(self, path: str, **kwargs) -> _Response:
        return _Response({"Policy": {"IsHidden": True}})

    def set_policy(self, user_id: str, policy: dict) -> None:
        self.policy_updates.append(policy)


def test_new_server_hides_users_by_default(session):
    server = _server()

    assert server.hide_users_from_login is True
    assert login_screen_policy(server) == {"IsHidden": True}


def test_option_off_shows_new_users(session):
    server = _server(hide_users_from_login=False)

    assert login_screen_policy(server) == {"IsHidden": False}


def test_emby_keeps_its_own_defaults(session):
    server = _server("emby", hide_users_from_login=False)

    assert login_screen_policy(server) == {}
    assert login_screen_policy(None) == {}


@pytest.mark.parametrize("hidden", [True, False])
def test_jellyfin_join_sends_the_option(session, hidden):
    server = _server(hide_users_from_login=hidden)
    db.session.add(Invitation(code="HIDECODE", used=False, unlimited=True))
    db.session.commit()
    client = _CapturingJellyfin(server)

    ok, message = client._do_join(
        "viewer", "password123", "password123", "viewer@example.com", "HIDECODE"
    )

    assert ok, message
    assert client.policy_updates[-1]["IsHidden"] is hidden
    assert User.query.filter_by(username="viewer").count() == 1


def test_password_prompt_sends_the_option(client, session):
    server = _server(hide_users_from_login=False)
    invitation = Invitation(code="HIDEPROMPT", used=False, unlimited=True)
    db.session.add(invitation)
    db.session.commit()
    db.session.execute(
        invitation_servers.insert().values(invite_id=invitation.id, server_id=server.id)
    )
    db.session.commit()
    media_client = _CapturingJellyfin(server)

    with patch(
        "app.services.media.service.get_client_for_media_server",
        return_value=media_client,
    ):
        client.post(
            "/j/HIDEPROMPT/password",
            data={
                "username": "viewer",
                "password": "password123",
                "confirm": "password123",
            },
        )

    assert media_client.policy_updates[-1]["IsHidden"] is False


SERVER_FORM = {
    "server_name": "Jellyfin",
    "server_type": "jellyfin",
    "server_url": "http://jellyfin.local",
    "api_key": "key",
}


def _hide_checked(html: str) -> bool:
    pattern = r'name="hide_users_from_login"\s+type="checkbox"\s+value="true"\s+checked'
    return re.search(pattern, html) is not None


def _connection_check(ok: bool):
    return patch(
        "app.blueprints.media_servers.routes.check_server_connection",
        return_value=(ok, "" if ok else "Connection refused"),
    )


def test_server_modals_show_the_option(admin_client):
    server = _server(hide_users_from_login=False)

    create = admin_client.get("/settings/servers/create").get_data(as_text=True)
    edit = admin_client.get(f"/settings/servers/{server.id}/edit")

    assert _hide_checked(create)
    assert not _hide_checked(edit.get_data(as_text=True))


def test_create_modal_keeps_the_typed_option(admin_client):
    with _connection_check(ok=False):
        response = admin_client.post("/settings/servers/create", data=SERVER_FORM)

    assert "Connection refused" in response.get_data(as_text=True)
    assert not _hide_checked(response.get_data(as_text=True))


def test_edit_server_saves_the_option(admin_client):
    server = _server()

    with _connection_check(ok=True):
        admin_client.post(f"/settings/servers/{server.id}/edit", data=SERVER_FORM)
        db.session.refresh(server)
        assert server.hide_users_from_login is False

        form = {**SERVER_FORM, "hide_users_from_login": "true"}
        admin_client.post(f"/settings/servers/{server.id}/edit", data=form)
        db.session.refresh(server)
        assert server.hide_users_from_login is True


@pytest.fixture
def engine(tmp_path):
    """Give a new database at the revision before the option.

    The test runs in the app context of that database.
    """
    db_url = f"sqlite:///{tmp_path / 'migration.db'}"

    class Config(BaseConfig):
        TESTING = True
        SQLALCHEMY_DATABASE_URI = db_url

    app = create_app(Config)  # type: ignore[arg-type]
    engine = create_engine(db_url)
    with app.app_context():
        upgrade(revision=f"{REVISION}-1")
        yield engine
    engine.dispose()


def test_migration_keeps_existing_servers_hidden(engine):
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO media_server (name, server_type, url, verified,"
                " allow_downloads, allow_live_tv, allow_mobile_uploads, created_at)"
                " VALUES ('JF', 'jellyfin', 'http://jf', 1, 0, 0, 0, '2026-01-01')"
            )
        )

    upgrade(revision=REVISION)
    with engine.connect() as conn:
        hidden = conn.execute(
            text("SELECT hide_users_from_login FROM media_server")
        ).scalar()
    assert hidden == 1

    downgrade(revision=f"{REVISION}-1")
    with engine.connect() as conn:
        columns = {
            row[1] for row in conn.execute(text("PRAGMA table_info(media_server)"))
        }
    assert "hide_users_from_login" not in columns


def test_migration_keeps_rows_that_reference_the_server(engine):
    """A rebuild of media_server deletes child rows through ON DELETE CASCADE."""
    child_rows = text(
        'SELECT (SELECT count(*) FROM library), (SELECT count(*) FROM "user"),'
        " (SELECT count(*) FROM invitation_server),"
        " (SELECT server_id FROM invitation)"
    )
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO media_server (id, name, server_type, url, verified,"
                " allow_downloads, allow_live_tv, allow_mobile_uploads, created_at)"
                " VALUES (1, 'JF', 'jellyfin', 'http://jf', 1, 0, 0, 0, '2026-01-01')"
            )
        )
        conn.execute(
            text(
                "INSERT INTO library (external_id, name, enabled, server_id)"
                " VALUES ('L1', 'Movies', 1, 1)"
            )
        )
        conn.execute(
            text(
                'INSERT INTO "user" (token, username, code, server_id)'
                " VALUES ('t1', 'alice', 'c1', 1)"
            )
        )
        conn.execute(
            text(
                "INSERT INTO invitation (id, code, used, created, server_id)"
                " VALUES (1, 'INV1', 0, '2026-01-01', 1)"
            )
        )
        conn.execute(
            text(
                "INSERT INTO invitation_server (invite_id, server_id, used)"
                " VALUES (1, 1, 0)"
            )
        )
        # A failed run of the first version of this migration left this table.
        conn.execute(text("CREATE TABLE _alembic_tmp_media_server (id INTEGER)"))

    upgrade(revision=REVISION)
    with engine.connect() as conn:
        assert conn.execute(child_rows).one() == (1, 1, 1, 1)
        leftover = conn.execute(
            text(
                "SELECT name FROM sqlite_master"
                " WHERE name = '_alembic_tmp_media_server'"
            )
        ).first()
        assert leftover is None

    downgrade(revision=f"{REVISION}-1")
    with engine.connect() as conn:
        assert conn.execute(child_rows).one() == (1, 1, 1, 1)


def test_migration_skips_a_column_that_an_admin_added_by_hand(engine):
    with engine.begin() as conn:
        conn.execute(
            text(
                "ALTER TABLE media_server"
                " ADD COLUMN hide_users_from_login BOOLEAN DEFAULT 1 NOT NULL"
            )
        )

    upgrade(revision=REVISION)
    with engine.connect() as conn:
        version = conn.execute(text("SELECT version_num FROM alembic_version"))
        assert version.scalar() == REVISION
