"""Removing a user from one server keeps the row when that server refuses.

The per-server remove logged a failed remote delete and then deleted the Wizarr
row anyway, leaving the account on the server with nothing in Wizarr to find it
by. It now follows the same rule as the delete dialog: the server confirms
first (a user it no longer has counts as gone), otherwise the row stays and the
dialog names the account.
"""

from unittest.mock import Mock

import pytest
import requests

from app.extensions import db
from app.models import AdminAccount, MediaServer, User
from app.services.media import service

HX = {"HX-Request": "true"}


@pytest.fixture
def admin_client(client, session):
    admin = AdminAccount(username="testadmin")
    admin.set_password("TestPass123")
    session.add(admin)
    session.commit()
    client.post("/login", data={"username": "testadmin", "password": "TestPass123"})
    return client


def _server(session, name):
    row = MediaServer(
        name=name, server_type="audiobookshelf", url="http://x.local", api_key="k"
    )
    session.add(row)
    session.commit()
    return row


def _user(session, server, name):
    user = User(
        token=f"remote-{name}",
        username=name,
        email=f"{name}@example.com",
        code="CODE",
        server_id=server.id,
    )
    session.add(user)
    session.commit()
    return user


def _remote(monkeypatch, error):
    fake = Mock()
    if error is None:
        fake.delete_user.return_value = None
    else:
        fake.delete_user.side_effect = error
    monkeypatch.setattr(service, "get_client_for_media_server", lambda _server: fake)
    return fake


def _exists(user_id):
    return db.session.get(User, user_id) is not None


def _remove(client, user, server):
    return client.post(f"/users/{user.id}/remove-from-server/{server.id}", headers=HX)


def test_a_refused_remove_keeps_the_row_and_names_the_account(
    admin_client, session, monkeypatch
):
    abs_ = _server(session, "ABS")
    user = _user(session, abs_, "quinn")
    _remote(monkeypatch, RuntimeError("down"))

    response = _remove(admin_client, user, abs_)

    assert _exists(user.id)
    body = response.get_data(as_text=True)
    assert "quinn" in body
    assert "ABS" in body


def test_a_confirmed_remove_deletes_the_row(admin_client, session, monkeypatch):
    abs_ = _server(session, "ABS")
    user = _user(session, abs_, "quinn")
    _remote(monkeypatch, None)

    response = _remove(admin_client, user, abs_)

    assert response.status_code == 200
    assert not _exists(user.id)


def test_a_user_the_server_no_longer_has_counts_as_removed(
    admin_client, session, monkeypatch
):
    abs_ = _server(session, "ABS")
    user = _user(session, abs_, "quinn")
    gone = requests.HTTPError("404")
    gone.response = Mock(status_code=404)
    _remote(monkeypatch, gone)

    _remove(admin_client, user, abs_)

    assert not _exists(user.id)


def test_the_service_call_without_the_flag_still_deletes_locally(session, monkeypatch):
    """Other callers keep their behaviour unless they ask for the rule."""
    abs_ = _server(session, "ABS")
    user = _user(session, abs_, "quinn")
    _remote(monkeypatch, RuntimeError("down"))

    assert service.remove_user_from_server(user.id, abs_.id) is True
    assert not _exists(user.id)
