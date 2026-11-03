"""Real workflow + persistent SQLite + stateful HTTP Emby boundary tests."""

import hashlib
import json
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from app.extensions import db
from app.models import ApiKey, Invitation, MediaServer, invitation_users
from app.services.invitation_flow.workflows import FormBasedWorkflow


@contextmanager
def emby_sink_server():
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
    try:
        yield sink
    finally:
        sink.release.set()
        server.shutdown()
        server.server_close()
        thread.join()


@pytest.fixture
def emby_sink():
    with emby_sink_server() as sink:
        yield sink


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
        assert server is not None
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
    app, client, access_fixture, emby_sink, monkeypatch
):
    """Create -> committed DELETE -> workflow lookup, ordered without sleeps."""
    from app.services.media.emby import EmbyClient

    iid, sid, headers = access_fixture
    created, resume = threading.Event(), threading.Event()
    original = EmbyClient.create_user

    def create(self, username, password):
        uid = original(self, username, password)
        created.set()
        assert resume.wait(10)
        return uid

    monkeypatch.setattr(EmbyClient, "create_user", create)
    with ThreadPoolExecutor(max_workers=1) as pool:
        joining = pool.submit(join, app, sid)
        assert created.wait(10)
        try:
            response = client.delete(f"/api/invitations/{iid}", headers=headers)
            assert response.status_code == 200
        finally:
            resume.set()
        joining.result(timeout=15)
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
    inv = db.session.get(Invitation, iid)
    assert inv is not None
    inv.used = True
    session.commit()
    response = client.post(f"/api/invitations/{iid}/revoke", headers=headers)
    assert response.status_code == 202
    assert response.get_json()["account_ids_complete"] is False


def test_revocation_requires_api_key(client, access_fixture):
    iid, _, _ = access_fixture
    assert client.post(f"/api/invitations/{iid}/revoke").status_code == 401


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("post", "/api/invitations/999999/revoke"),
        ("get", "/api/invitations/revocations/missing"),
        ("post", "/api/invitations/revocations/missing"),
    ],
)
def test_revocation_targets_require_auth_and_unknown_targets_have_no_effect(
    client, access_fixture, emby_sink, method, path
):
    _, _, headers = access_fixture
    assert getattr(client, method)(path).status_code == 401
    assert (
        getattr(client, method)(path, headers={"X-API-Key": "invalid"}).status_code
        == 401
    )
    response = getattr(client, method)(path, headers=headers)
    assert response.status_code == 404
    assert "error" in response.get_json()
    assert emby_sink.calls == []


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
    assert inv is not None
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
    server = db.session.get(MediaServer, sid)
    assert server is not None
    server.url += "/different-server"
    session.commit()
    before = len(emby_sink.calls)
    response = client.post(f"/api/invitations/{iid}/revoke", headers=headers)
    assert response.status_code == 202
    assert emby_sink.calls[before:] == []


@pytest.mark.parametrize("cutoff_between_servers", [False, True])
def test_two_http_backends_in_one_workflow(
    app, client, access_fixture, session, emby_sink, monkeypatch, cutoff_between_servers
):
    from app.services.media.emby import EmbyClient

    iid, sid, headers = access_fixture
    with emby_sink_server() as second_sink:
        other = MediaServer(
            name="Second Emby",
            server_type="emby",
            url=second_sink.url,
            api_key="synthetic",
        )
        inv = db.session.get(Invitation, iid)
        assert inv is not None
        inv.servers.append(other)
        session.commit()
        ids = [sid, other.id]
        session.commit()
        first_done, resume = threading.Event(), threading.Event()
        original = EmbyClient.join

        def guarded_join(self, *args, **kwargs):
            result = original(self, *args, **kwargs)
            if cutoff_between_servers and self.server_id == sid:
                first_done.set()
                assert resume.wait(10)
            return result

        monkeypatch.setattr(EmbyClient, "join", guarded_join)

        def run():
            with app.test_request_context("/join"):
                servers = []
                for server_id in ids:
                    server = db.session.get(MediaServer, server_id)
                    assert server is not None
                    servers.append(server)
                return FormBasedWorkflow()._process_servers(
                    servers,
                    {
                        "username": "multi",
                        "email": "multi@example.test",
                        "password": "Testpass123!",
                        "confirm_password": "Testpass123!",
                    },
                    "REVOKE1",
                )

        with ThreadPoolExecutor(max_workers=1) as pool:
            joining = pool.submit(run)
            try:
                if cutoff_between_servers:
                    assert first_done.wait(10)
                    assert (
                        client.post(
                            f"/api/invitations/{iid}/revoke", headers=headers
                        ).status_code
                        == 200
                    )
            finally:
                resume.set()
            successful, failed = joining.result(timeout=20)
        assert len(successful) == (1 if cutoff_between_servers else 2)
        assert len(failed) == (1 if cutoff_between_servers else 0)
        result = client.post(f"/api/invitations/{iid}/revoke", headers=headers)
        assert result.status_code == 200
        accounts = {
            (a["server_id"], a["remote_user_id"]) for a in result.get_json()["accounts"]
        }
        expected = (
            {(sid, "remote-1")}
            if cutoff_between_servers
            else {(sid, "remote-1"), (ids[1], "remote-1")}
        )
        assert accounts == expected
        assert emby_sink.users["remote-1"]["Policy"]["IsDisabled"] is True
        if cutoff_between_servers:
            assert second_sink.users == {}
        else:
            assert second_sink.users["remote-1"]["Policy"]["IsDisabled"] is True


@pytest.mark.parametrize("unsupported", ["ldap", "mixed", "server_type"])
def test_removed_unsupported_config_never_restores_identity_completeness(
    app, client, access_fixture, session, unsupported
):
    iid, sid, headers = access_fixture
    assert join(app, sid)[0]
    inv = db.session.get(Invitation, iid)
    assert inv is not None
    if unsupported == "ldap":
        inv.create_ldap_user = True
        session.commit()
        inv.create_ldap_user = False
    elif unsupported == "server_type":
        server = db.session.get(MediaServer, sid)
        assert server is not None
        server.server_type = "jellyfin"
        session.commit()
        server.server_type = "emby"
    else:
        other = MediaServer(
            name="Unsupported",
            server_type="jellyfin",
            url="http://unused.invalid",
            api_key="synthetic",
        )
        inv.servers.append(other)
        session.commit()
        inv.servers.remove(other)
    session.commit()
    result = client.post(f"/api/invitations/{iid}/revoke", headers=headers)
    assert result.status_code == 202
    assert result.get_json()["account_ids_complete"] is False


@pytest.mark.parametrize("after_delete", [False, True])
def test_unsupported_config_cannot_inherit_complete_emby_provenance(
    app, client, access_fixture, session, after_delete
):
    iid, sid, headers = access_fixture
    assert join(app, sid)[0]
    inv = db.session.get(Invitation, iid)
    assert inv is not None
    inv.create_ldap_user = True
    session.commit()
    path = f"/api/invitations/{iid}/revoke"
    if after_delete:
        operation = client.delete(
            f"/api/invitations/{iid}", headers=headers
        ).get_json()["operation_id"]
        path = f"/api/invitations/revocations/{operation}"
    response = client.post(path, headers=headers)
    assert response.status_code == 202
    assert response.get_json()["account_ids_complete"] is False
