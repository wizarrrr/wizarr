"""New Audiobookshelf users get "Can create e-reader" with downloads; updates leave it alone."""

from unittest.mock import Mock

from app.services.media.audiobookshelf import AudiobookshelfClient

API = AudiobookshelfClient.API_PREFIX


def _client(current_user=None):
    client = AudiobookshelfClient.__new__(AudiobookshelfClient)
    response = Mock(status_code=200)
    response.json.return_value = {"id": "abs-1", "user": {"id": "abs-1"}}
    client.post = Mock(return_value=response)
    client.patch = Mock(return_value=response)
    client.get = Mock(
        return_value=Mock(json=Mock(return_value=current_user or {"permissions": {}}))
    )
    client.get_user = Mock(return_value=current_user or {"permissions": {}})
    client._handle_response_error = Mock()
    return client


def _created_permissions(client):
    return client.post.call_args.kwargs["json"]["permissions"]


def test_create_user_grants_ereader_to_regular_user():
    client = _client()
    client.create_user("sam", "pw", "sam@example.com")
    assert _created_permissions(client)["createEreader"] is True


def test_create_user_denies_ereader_to_guest():
    client = _client()
    client.create_user("sam", "pw", "sam@example.com", allow_downloads=False)
    assert _created_permissions(client)["createEreader"] is False


def test_create_user_grants_ereader_to_admin():
    client = _client()
    client.create_user(
        "sam", "pw", "sam@example.com", is_admin=True, allow_downloads=False
    )
    assert _created_permissions(client)["createEreader"] is True


def test_update_user_permissions_keeps_existing_ereader_permission():
    # Changing download access must not grant or remove e-reader access set by an admin.
    client = _client({"permissions": {"download": True, "createEreader": True}})
    client.update_user_permissions("abs-1", {"allow_downloads": False})
    perms = client.patch.call_args.kwargs["json"]["permissions"]
    assert perms["download"] is False
    assert perms["createEreader"] is True


def test_set_specific_libraries_keeps_existing_ereader_permission():
    client = _client({"permissions": {"download": True, "createEreader": False}})
    client.update_user = Mock()
    client._set_specific_libraries("abs-1", ["lib-1"], allow_downloads=True)
    patch = client.update_user.call_args.args[1]
    assert patch["permissions"]["createEreader"] is False
    assert patch["permissions"]["download"] is True
