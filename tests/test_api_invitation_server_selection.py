"""POST /api/invitations requires explicit server_ids, also with one server."""

import hashlib

import pytest

from app.models import ApiKey, Invitation, MediaServer

RAW_KEY = "test_api_key_12345"


@pytest.fixture
def api_key(session, admin_user):
    session.add(
        ApiKey(
            name="Test API Key",
            key_hash=hashlib.sha256(RAW_KEY.encode()).hexdigest(),
            created_by_id=admin_user.id,
            is_active=True,
        )
    )
    session.commit()
    return RAW_KEY


def _add_servers(session, *specs):
    servers = [
        MediaServer(
            name=name,
            server_type="plex",
            url="http://localhost:32400",
            api_key="test_key",
            verified=verified,
        )
        for name, verified in specs
    ]
    session.add_all(servers)
    session.commit()
    return servers


def _create(client, api_key, **data):
    return client.post(
        "/api/invitations",
        headers={"X-API-Key": api_key},
        json={"duration": "30", "unlimited": False, **data},
    )


@pytest.mark.parametrize(
    ("server_specs", "available"),
    [
        ([("Only Server", True)], ["Only Server"]),
        ([("Server 1", True), ("Server 2", True)], ["Server 1", "Server 2"]),
        ([("Unverified Server", False)], []),
        (
            [("Verified Server", True), ("Unverified Server", False)],
            ["Verified Server"],
        ),
    ],
    ids=["one-server", "two-servers", "unverified-only", "mixed"],
)
def test_missing_server_ids_lists_verified_servers(
    client, session, api_key, server_specs, available
):
    _add_servers(session, *server_specs)

    response = _create(client, api_key)

    assert response.status_code == 400
    body = response.get_json()
    assert "Server selection is required" in body["error"]
    assert sorted(s["name"] for s in body["available_servers"]) == available
    assert Invitation.query.count() == 0


def test_explicit_server_selection(client, session, api_key):
    _server1, server2 = _add_servers(session, ("Server 1", True), ("Server 2", True))

    response = _create(client, api_key, server_ids=[server2.id])

    assert response.status_code == 201
    assert "invitation" in response.get_json()
    invitation = Invitation.query.one()
    assert [server.id for server in invitation.servers] == [server2.id]


def test_invalid_server_ids(client, session, api_key):
    _add_servers(session, ("Valid Server", True))

    response = _create(client, api_key, server_ids=[99999])

    assert response.status_code == 400
    assert "not found or not verified" in response.get_json()["error"]
