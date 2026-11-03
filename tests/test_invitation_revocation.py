"""Real workflow + persistent SQLite + stateful HTTP Emby boundary tests."""

import hashlib
import json
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from app.extensions import db
from app.models import ApiKey, Invitation, MediaServer, invitation_users
from app.services.invitation_flow.workflows import FormBasedWorkflow


@pytest.fixture
def emby_sink():
    class Sink:
        def __init__(self):
            self.users = {}
            self.calls = []
            self.created = threading.Event()
            self.release = threading.Event()

        url = ""
        fail_list = False
        pause_create = False
        fail_disable = False
        ignore_disable = False
        lose_create_response = False
        timeout_disable = False

    sink = Sink()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def reply(self, status, data=None):
            body = json.dumps(data).encode() if data is not None else b""
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            sink.calls.append(("GET", self.path))
            if self.path == "/Library/MediaFolders":
                return self.reply(200, {"Items": []})
            if self.path == "/Users":
                return self.reply(
                    503 if sink.fail_list else 200, list(sink.users.values())
                )
            user = sink.users.get(self.path.split("/")[-1])
            return self.reply(200 if user else 404, user)

        def do_POST(self):
            data = json.loads(
                self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}"
            )
            sink.calls.append(("POST", self.path))
            if self.path == "/Users/New":
                uid = f"remote-{len(sink.users) + 1}"
                sink.users[uid] = {
                    "Id": uid,
                    "Name": data["Name"],
                    "Policy": {"IsDisabled": False},
                }
                sink.created.set()
                if sink.pause_create:
                    assert sink.release.wait(10), "test did not release create"
                if sink.lose_create_response:
                    self.close_connection = True
                    return None
                return self.reply(200, sink.users[uid])
            if self.path.endswith("/Policy"):
                if data.get("IsDisabled") and sink.fail_disable:
                    return self.reply(503)
                uid = self.path.split("/")[2]
                if not (data.get("IsDisabled") and sink.ignore_disable):
                    sink.users[uid]["Policy"] = data
                if data.get("IsDisabled") and sink.timeout_disable:
                    assert sink.release.wait(10)
                    self.close_connection = True
                    return None
            return self.reply(204)

        def do_DELETE(self):
            sink.calls.append(("DELETE", self.path))
            sink.users.pop(self.path.split("/")[-1], None)
            self.reply(204)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    sink.url = f"http://127.0.0.1:{server.server_port}"
    yield sink
    sink.release.set()
    server.shutdown()
    server.server_close()
    thread.join()


@pytest.fixture
def access_fixture(session, admin_user, emby_sink):
    key = "synthetic-revocation-key"
    session.add(
        ApiKey(
            name="test",
            key_hash=hashlib.sha256(key.encode()).hexdigest(),
            created_by_id=admin_user.id,
            is_active=True,
        )
    )
    server = MediaServer(
        name="Synthetic Emby",
        server_type="emby",
        url=emby_sink.url,
        api_key="synthetic",
        verified=True,
    )
    invite = Invitation(code="REVOKE1", unlimited=True, servers=[server])
    session.add_all([server, invite])
    session.commit()
    return invite.id, server.id, {"X-API-Key": key}


def join(app, server_id, username="joiner"):
    with app.test_request_context("/join"):
        server = db.session.get(MediaServer, server_id)
        return FormBasedWorkflow()._process_servers(
            [server],
            {
                "username": username,
                "email": f"{username}@example.test",
                "password": "Testpass123!",
                "confirm_password": "Testpass123!",
            },
            "REVOKE1",
        )


def test_delete_during_remote_creation_preserves_provenance(
    app, client, access_fixture, emby_sink
):
    """Base RED: DELETE can erase the only invitation/account association."""
    iid, sid, headers = access_fixture
    emby_sink.pause_create = True
    with ThreadPoolExecutor(max_workers=2) as pool:
        joining = pool.submit(join, app, sid)
        assert emby_sink.created.wait(10)

        # DELETE must serialize with remote creation, not wait on this test thread.
        def delete():
            with app.test_client() as other:
                return other.delete(f"/api/invitations/{iid}", headers=headers)

        deleting = pool.submit(delete)
        emby_sink.release.set()
        joining.result(timeout=15)
        response = deleting.result(timeout=15)
    assert response.status_code == 200
    assert len(emby_sink.users) == 1
    assert db.session.get(Invitation, iid) is None
    assert db.session.execute(db.select(invitation_users)).all() == []
    # The replacement must preserve actual IDs independently of the invitation.
    from sqlalchemy import inspect

    assert "invitation_join_attempt" in inspect(db.engine).get_table_names(), (
        "remote account survived DELETE without durable join provenance"
    )
    from app.models import InvitationJoinAttempt

    attempts = InvitationJoinAttempt.query.all()
    assert [a.remote_user_id for a in attempts] == ["remote-1"]


def test_revoke_before_join_is_idempotent_and_blocks_create(
    app, client, access_fixture, emby_sink
):
    iid, sid, headers = access_fixture
    first = client.post(f"/api/invitations/{iid}/revoke", headers=headers)
    assert first.status_code == 200
    status = first.get_json()
    assert status["state"] == "revoked"
    assert status["barrier_committed"] is True
    assert status["account_ids_complete"] is True
    assert status["in_flight_joins"] == 0
    assert (
        client.post(f"/api/invitations/{iid}/revoke", headers=headers).get_json()
        == status
    )
    assert join(app, sid)[0] == []
    assert emby_sink.users == {}


@pytest.mark.parametrize("failure", ["none", "fail_disable", "ignore_disable"])
def test_revoke_reads_back_remote_policy_and_never_deletes(
    app, client, access_fixture, emby_sink, failure
):
    iid, sid, headers = access_fixture
    assert join(app, sid)[0]
    if failure != "none":
        setattr(emby_sink, failure, True)
    response = client.post(f"/api/invitations/{iid}/revoke", headers=headers)
    assert response.status_code == (200 if failure == "none" else 202)
    data = response.get_json()
    assert data["state"] == ("revoked" if failure == "none" else "pending")
    assert data["accounts"][0]["remote_user_id"] == "remote-1"
    assert emby_sink.users["remote-1"]["Policy"]["IsDisabled"] is (failure == "none")
    assert not any(method == "DELETE" for method, _ in emby_sink.calls)
    emby_sink.fail_disable = False
    emby_sink.ignore_disable = False
    assert (
        client.post(f"/api/invitations/{iid}/revoke", headers=headers).get_json()[
            "state"
        ]
        == "revoked"
    )


def test_lost_create_response_survives_session_restart_without_retry(
    app, client, access_fixture, emby_sink
):
    iid, sid, headers = access_fixture
    emby_sink.lose_create_response = True
    assert join(app, sid)[0] == []
    db.session.remove()
    assert join(app, sid, "retry")[0] == []
    status = client.post(f"/api/invitations/{iid}/revoke", headers=headers).get_json()
    assert status["state"] == "pending"
    assert status["account_ids_complete"] is False
    assert status["in_flight_joins"] == 1
    assert len(emby_sink.users) == 1
    assert (
        len(
            [
                p
                for method, p in emby_sink.calls
                if method == "POST" and p == "/Users/New"
            ]
        )
        == 1
    )


def test_disable_timeout_preserves_identity_and_retry_confirms_effect(
    app, client, access_fixture, emby_sink, monkeypatch
):
    from app.services.media.emby import EmbyClient

    iid, sid, headers = access_fixture
    assert join(app, sid)[0]
    monkeypatch.setattr(EmbyClient, "timeout", (1, 0.1))
    emby_sink.timeout_disable = True
    response = client.post(f"/api/invitations/{iid}/revoke", headers=headers)
    assert response.status_code == 202
    assert response.get_json()["accounts"][0]["remote_user_id"] == "remote-1"
    assert response.get_json()["accounts"][0]["remote_state"] == "unconfirmed"
    emby_sink.release.set()
    emby_sink.timeout_disable = False
    assert emby_sink.users["remote-1"]["Policy"]["IsDisabled"] is True
    assert (
        client.post(f"/api/invitations/{iid}/revoke", headers=headers).status_code
        == 200
    )
    assert not any(method == "DELETE" for method, _ in emby_sink.calls)


def test_multiple_accounts_are_all_confirmed_and_duplicate_revoke_does_not_write_again(
    app, client, access_fixture, emby_sink
):
    iid, sid, headers = access_fixture
    assert join(app, sid, "one")[0]
    assert join(app, sid, "two")[0]
    response = client.post(f"/api/invitations/{iid}/revoke", headers=headers)
    assert response.status_code == 200
    status = response.get_json()
    assert {a["remote_user_id"] for a in status["accounts"]} == set(emby_sink.users)
    assert len(status["accounts"]) == 2
    assert all(u["Policy"]["IsDisabled"] for u in emby_sink.users.values())
    writes = [call for call in emby_sink.calls if call[0] == "POST"]
    db.session.remove()
    assert (
        client.post(f"/api/invitations/{iid}/revoke", headers=headers).get_json()
        == status
    )
    assert [call for call in emby_sink.calls if call[0] == "POST"] == writes
    operation = status["operation_id"]
    before = list(emby_sink.calls)
    assert (
        client.get(
            f"/api/invitations/revocations/{operation}", headers=headers
        ).get_json()
        == status
    )
    assert emby_sink.calls == before
    assert "token" not in json.dumps(status)
    assert "synthetic" not in json.dumps(status)


def test_legacy_used_invitation_is_never_complete(client, access_fixture, session):
    iid, _, headers = access_fixture
    db.session.get(Invitation, iid).used = True
    session.commit()
    response = client.post(f"/api/invitations/{iid}/revoke", headers=headers)
    assert response.status_code == 202
    assert response.get_json()["account_ids_complete"] is False


def test_revocation_requires_api_key(client, access_fixture):
    iid, _, _ = access_fixture
    assert client.post(f"/api/invitations/{iid}/revoke").status_code == 401


def test_legacy_password_route_cannot_bypass_cutoff(client, access_fixture, emby_sink):
    iid, _, headers = access_fixture
    assert (
        client.post(f"/api/invitations/{iid}/revoke", headers=headers).status_code
        == 200
    )
    response = client.post(
        "/j/REVOKE1/password",
        data={
            "username": "legacy",
            "email": "legacy@example.test",
            "password": "Testpass123!",
            "confirm": "Testpass123!",
        },
    )
    assert response.status_code in (200, 302)
    assert emby_sink.users == {}


def test_unified_public_route_tracks_actual_ids(client, access_fixture, emby_sink):
    iid, _, headers = access_fixture
    response = client.post(
        "/invitation/process",
        data={
            "code": "REVOKE1",
            "username": "publicjoin",
            "email": "publicjoin@example.com",
            "password": "Testpass123!",
            "confirm_password": "Testpass123!",
        },
    )
    assert response.status_code == 302
    assert len(emby_sink.users) == 1
    result = client.post(f"/api/invitations/{iid}/revoke", headers=headers)
    assert result.status_code == 200
    assert result.get_json()["accounts"][0]["remote_user_id"] == "remote-1"
    assert emby_sink.users["remote-1"]["Policy"]["IsDisabled"] is True


def test_deleted_invitation_can_be_explicitly_revoked_by_stable_operation(
    app, client, access_fixture, emby_sink
):
    iid, sid, headers = access_fixture
    assert join(app, sid)[0]
    response = client.delete(f"/api/invitations/{iid}", headers=headers)
    assert response.status_code == 200
    assert emby_sink.users["remote-1"]["Policy"]["IsDisabled"] is False
    operation_id = response.get_json()["operation_id"]
    result = client.post(
        f"/api/invitations/revocations/{operation_id}", headers=headers
    )
    assert result.status_code == 200
    assert result.get_json()["state"] == "revoked"
    assert emby_sink.users["remote-1"]["Policy"]["IsDisabled"] is True


WORKER = """
import os, sys
from app import create_app
from app.config import BaseConfig
from app.extensions import db
from app.models import MediaServer
from app.services.media.service import get_client_for_media_server
from app.services.media.client_base import RestApiMixin
class Config(BaseConfig):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = sys.argv[1]
app = create_app(Config)
original = RestApiMixin.post
if sys.argv[3] == 'crash':
    def post(self, path, **kwargs):
        response = original(self, path, **kwargs)
        if path == '/Users/New':
            os._exit(73)
        return response
    RestApiMixin.post = post
with app.test_request_context('/join'):
    client = get_client_for_media_server(db.session.get(MediaServer, int(sys.argv[2])))
    result = client.join('worker', 'Testpass123!', 'Testpass123!', 'worker@example.test', 'REVOKE1')
    sys.exit(0 if result[0] else 2)
"""


def test_process_crash_after_remote_create_before_identity_commit(
    app, client, access_fixture, emby_sink
):
    iid, sid, headers = access_fixture
    uri = app.config["SQLALCHEMY_DATABASE_URI"]
    crashed = subprocess.run(  # noqa: S603 - fixed Python worker, synthetic local DB only
        [sys.executable, "-c", WORKER, uri, str(sid), "crash"],
        capture_output=True,
        timeout=30,
        check=False,
    )
    assert crashed.returncode == 73, crashed.stderr.decode()
    assert len(emby_sink.users) == 1
    db.session.remove()
    retried = subprocess.run(  # noqa: S603 - fixed Python worker, synthetic local DB only
        [sys.executable, "-c", WORKER, uri, str(sid), "retry"],
        capture_output=True,
        timeout=30,
        check=False,
    )
    assert retried.returncode == 2, retried.stderr.decode()
    result = client.post(f"/api/invitations/{iid}/revoke", headers=headers).get_json()
    assert result["state"] == "pending"
    assert result["in_flight_joins"] == 1
    assert result["account_ids_complete"] is False
    assert len(emby_sink.users) == 1
    assert emby_sink.users["remote-1"]["Policy"]["IsDisabled"] is False


def test_two_processes_share_durable_attempt_barrier(
    app, client, access_fixture, emby_sink
):
    iid, sid, headers = access_fixture
    emby_sink.pause_create = True
    uri = app.config["SQLALCHEMY_DATABASE_URI"]
    with subprocess.Popen(  # noqa: S603 - fixed Python worker, synthetic local DB only
        [sys.executable, "-c", WORKER, uri, str(sid), "join"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ) as worker:
        assert emby_sink.created.wait(10)
        with ThreadPoolExecutor(max_workers=1) as pool:
            second = pool.submit(join, app, sid, "second")
            emby_sink.release.set()
            second.result(timeout=15)
        _, stderr = worker.communicate(timeout=30)
        assert worker.returncode == 0, stderr.decode()
    response = client.post(f"/api/invitations/{iid}/revoke", headers=headers)
    assert response.status_code == 200
    result = response.get_json()
    assert result["in_flight_joins"] == 0
    assert len(result["accounts"]) == len(emby_sink.users)
    assert all(user["Policy"]["IsDisabled"] for user in emby_sink.users.values())


def test_cutoff_between_registration_and_remote_create(
    app, client, access_fixture, emby_sink
):
    from app.services.invitation_revocation import (
        JoinClosed,
        finish_join,
        guarded_post,
        register_join,
    )

    iid, sid, headers = access_fixture
    attempt = register_join("REVOKE1", sid)
    result = client.post(f"/api/invitations/{iid}/revoke", headers=headers).get_json()
    assert result["state"] == "pending"
    assert result["in_flight_joins"] == 1

    def forbidden():
        pytest.fail("remote write after cutoff")

    with pytest.raises(JoinClosed):
        guarded_post(attempt, "/Users/New", forbidden)
    finish_join(attempt)
    assert (
        client.post(f"/api/invitations/{iid}/revoke", headers=headers).get_json()[
            "state"
        ]
        == "revoked"
    )
    assert emby_sink.users == {}


def test_known_ids_survive_local_user_deletion_but_404_is_not_confirmation(
    app, client, access_fixture, emby_sink, session
):
    from app.models import User

    iid, sid, headers = access_fixture
    assert join(app, sid)[0]
    session.query(User).delete()
    session.commit()
    # A missing local row must not prevent authoritative disable of the saved ID.
    assert (
        client.post(f"/api/invitations/{iid}/revoke", headers=headers).get_json()[
            "state"
        ]
        == "revoked"
    )
    emby_sink.users.clear()
    # Emby's documented 404 also means unavailable; do not claim absence from it.
    result = client.post(f"/api/invitations/{iid}/revoke", headers=headers)
    assert result.status_code == 202
    assert result.get_json()["accounts"][0]["remote_state"] == "unconfirmed"


def test_reusing_deleted_code_cannot_bypass_tombstone(
    app, client, access_fixture, session, emby_sink
):
    from app.services.invites import create_invite

    iid, sid, headers = access_fixture
    assert client.delete(f"/api/invitations/{iid}", headers=headers).status_code == 200
    with pytest.raises(ValueError, match="duplicate"):
        create_invite({"code": "REVOKE1", "server_ids": [str(sid)]})
    # Also fail closed if a legacy/direct writer inserts the old code anyway.
    session.add(Invitation(code="REVOKE1", unlimited=True, server_id=sid))
    session.commit()
    assert join(app, sid)[0] == []
    assert emby_sink.users == {}


def test_cutoff_after_create_before_remaining_permissions(
    app, client, access_fixture, emby_sink, monkeypatch
):
    from app.services.media.emby import EmbyClient

    iid, sid, headers = access_fixture
    ready, resume = threading.Event(), threading.Event()
    original = EmbyClient.create_user

    def create(self, username, password):
        uid = original(self, username, password)
        ready.set()
        assert resume.wait(10)
        return uid

    monkeypatch.setattr(EmbyClient, "create_user", create)
    with ThreadPoolExecutor(max_workers=1) as pool:
        joining = pool.submit(join, app, sid)
        assert ready.wait(10)
        response = client.post(f"/api/invitations/{iid}/revoke", headers=headers)
        assert response.status_code == 202
        assert response.get_json()["in_flight_joins"] == 1
        assert emby_sink.users["remote-1"]["Policy"]["IsDisabled"] is True
        call_count = len(emby_sink.calls)
        resume.set()
        assert joining.result(timeout=15)[0] == []
    assert not any(
        method == "POST" and path.endswith("/Policy")
        for method, path in emby_sink.calls[call_count:]
    )
    status = client.post(f"/api/invitations/{iid}/revoke", headers=headers).get_json()
    assert status["state"] == "revoked"


def test_multiserver_partial_create_tracks_all_known_ids_and_unknowns(
    app, client, access_fixture, session, emby_sink
):
    iid, sid, headers = access_fixture
    assert join(app, sid)[0]
    other = MediaServer(
        name="Uncertain Emby",
        server_type="emby",
        url=emby_sink.url + "/unavailable",
        api_key="synthetic",
    )
    session.add(other)
    inv = db.session.get(Invitation, iid)
    inv.servers.append(other)
    session.commit()
    assert join(app, other.id)[0] == []
    result = client.post(f"/api/invitations/{iid}/revoke", headers=headers).get_json()
    assert result["state"] == "pending"
    assert result["account_ids_complete"] is False
    assert result["in_flight_joins"] == 1
    assert result["accounts"][0]["server_id"] == sid
    assert emby_sink.users["remote-1"]["Policy"]["IsDisabled"] is True


def test_changed_server_endpoint_is_not_used_to_revoke_old_identity(
    app, client, access_fixture, session, emby_sink
):
    iid, sid, headers = access_fixture
    assert join(app, sid)[0]
    db.session.get(MediaServer, sid).url += "/different-server"
    session.commit()
    before = len(emby_sink.calls)
    response = client.post(f"/api/invitations/{iid}/revoke", headers=headers)
    assert response.status_code == 202
    assert emby_sink.calls[before:] == []


def test_unsupported_config_cannot_inherit_complete_emby_provenance(
    app, client, access_fixture, session
):
    iid, sid, headers = access_fixture
    assert join(app, sid)[0]
    db.session.get(Invitation, iid).create_ldap_user = True
    session.commit()
    response = client.post(f"/api/invitations/{iid}/revoke", headers=headers)
    assert response.status_code == 202
    assert response.get_json()["account_ids_complete"] is False
