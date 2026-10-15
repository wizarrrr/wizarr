"""A batch of Ombi deletions downloads the Ombi user list one time.

Before, each deleted user downloaded the full Ombi user list again.
"""

from unittest.mock import Mock

import pytest

from app.models import Connection
from app.services.companions import ombi as ombi_module
from app.services.companions.ombi import OmbiClient

OMBI_USERS = [
    {"id": "o1", "userName": "alice"},
    {"id": "o2", "userName": "bob"},
    {"id": "o3", "userName": "carol"},
]


@pytest.fixture(autouse=True)
def _clear_cache():
    ombi_module.invalidate_user_list_cache()
    yield
    ombi_module.invalidate_user_list_cache()


def _connection(connection_id=1, api_key="ombi-key"):
    return Connection(
        id=connection_id,
        name="Ombi",
        connection_type="ombi",
        url="http://ombi.local",
        api_key=api_key,
    )


@pytest.fixture
def http(monkeypatch):
    session = Mock()
    session.get.return_value.json.side_effect = lambda: list(OMBI_USERS)
    session.delete.return_value.status_code = 204
    monkeypatch.setattr(ombi_module, "get_http_session", lambda: session)
    return session


def test_batch_of_deletions_downloads_the_list_once(http):
    client, connection = OmbiClient(), _connection()

    results = [client.delete_user(name, connection) for name in ("alice", "bob")]

    assert [r["status"] for r in results] == ["success", "success"]
    assert http.get.call_count == 1
    deleted = [call.args[0] for call in http.delete.call_args_list]
    assert deleted == [
        "http://ombi.local/api/v1/Identity/o1",
        "http://ombi.local/api/v1/Identity/o2",
    ]


def test_deleted_user_leaves_the_cached_list(http):
    client, connection = OmbiClient(), _connection()
    client.delete_user("alice", connection)

    result = client.delete_user("alice", connection)

    assert result["status"] == "warning"
    assert http.delete.call_count == 1


def test_each_connection_has_its_own_list(http):
    client = OmbiClient()

    client.delete_user("alice", _connection(1))
    client.delete_user("bob", _connection(2, api_key="other-key"))

    assert http.get.call_count == 2


def test_cached_list_expires(http, monkeypatch):
    monkeypatch.setattr(ombi_module, "USER_LIST_TTL", 0.0)
    client, connection = OmbiClient(), _connection()

    client.delete_user("alice", connection)
    client.delete_user("bob", connection)

    assert http.get.call_count == 2


def test_create_invalidates_the_cached_list(http, monkeypatch):
    client, connection = OmbiClient(), _connection()
    client.delete_user("alice", connection)
    post = Mock()
    post.return_value.status_code = 201
    monkeypatch.setattr(ombi_module.requests, "post", post)

    assert client.invite_user("dave", "dave@example.com", connection)["status"] == (
        "success"
    )
    client.delete_user("bob", connection)

    assert http.get.call_count == 2


def test_failed_delete_invalidates_the_cached_list(http):
    client, connection = OmbiClient(), _connection()
    http.delete.return_value.status_code = 500

    assert client.delete_user("alice", connection)["status"] == "error"
    client.delete_user("bob", connection)

    assert http.get.call_count == 2


def test_unexpected_list_response_is_an_error(http):
    http.get.return_value.json.side_effect = lambda: {"error": "unauthorized"}

    result = OmbiClient().delete_user("alice", _connection())

    assert result["status"] == "error"
    http.delete.assert_not_called()
