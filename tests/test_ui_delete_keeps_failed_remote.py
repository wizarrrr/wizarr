"""Deleting a user in the UI keeps the row when the server refuses.

The delete dialog and the bulk Delete button removed the Wizarr row even when
the media server could not be reached or refused the delete, so the account
stayed on the server with nothing in Wizarr to find it by. Both now require the
server to confirm (a user the server no longer has counts as gone): a failed
remote delete keeps the local row and says which account was not removed.
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


def _remote(monkeypatch, behaviour):
    """behaviour: {server name: exception to raise, or None for success}."""

    def client_for(server):
        fake = Mock()
        error = behaviour.get(server.name)
        if error is None:
            fake.delete_user.return_value = None
        else:
            fake.delete_user.side_effect = error
        return fake

    monkeypatch.setattr(service, "get_client_for_media_server", client_for)


def _exists(user_id):
    return db.session.get(User, user_id) is not None


def _post(client, path, field, *ids):
    return client.post(path, data={field: [str(i) for i in ids]}, headers=HX)


@pytest.mark.parametrize(
    ("path", "field"),
    [
        ("/users/process-deletion", "server_accounts"),
        ("/users/bulk-delete", "uids"),
    ],
)
class TestDeleteFromTheUi:
    def test_a_failed_remote_delete_keeps_the_row_and_says_so(
        self, admin_client, session, monkeypatch, path, field
    ):
        abs_ = _server(session, "ABS")
        user = _user(session, abs_, "sam")
        _remote(monkeypatch, {"ABS": RuntimeError("down")})

        resp = _post(admin_client, path, field, user.id)

        assert _exists(user.id)
        body = resp.get_data(as_text=True)
        assert "sam" in body
        assert "ABS" in body
        assert "could not be removed" in body
        assert resp.headers["HX-Retarget"] == "#modal-user"

    def test_a_confirmed_delete_removes_the_row(
        self, admin_client, session, monkeypatch, path, field
    ):
        abs_ = _server(session, "ABS")
        user = _user(session, abs_, "sam")
        _remote(monkeypatch, {})

        resp = _post(admin_client, path, field, user.id)

        assert not _exists(user.id)
        assert "HX-Retarget" not in resp.headers

    def test_a_user_the_server_no_longer_has_counts_as_deleted(
        self, admin_client, session, monkeypatch, path, field
    ):
        abs_ = _server(session, "ABS")
        user = _user(session, abs_, "sam")
        gone = requests.HTTPError(response=Mock(status_code=404))
        _remote(monkeypatch, {"ABS": gone})

        _post(admin_client, path, field, user.id)

        assert not _exists(user.id)

    def test_one_failure_does_not_stop_the_others(
        self, admin_client, session, monkeypatch, path, field
    ):
        broken = _server(session, "Broken")
        fine = _server(session, "Fine")
        keep = _user(session, broken, "sam")
        drop = _user(session, fine, "quinn")
        _remote(monkeypatch, {"Broken": RuntimeError("down")})

        resp = _post(admin_client, path, field, keep.id, drop.id)

        assert _exists(keep.id)
        assert not _exists(drop.id)
        body = resp.get_data(as_text=True)
        assert "sam" in body
        assert "quinn" not in body
