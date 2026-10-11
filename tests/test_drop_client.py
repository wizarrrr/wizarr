"""
Drop creates a user in two calls: an admin invitation, then a Simple
Authentication sign-up that uses it. The client used an old invitation path,
sent an invalid ``expires`` date, and padded short passwords with zeros, so the
user could not log in with the password they chose.
"""

from datetime import datetime
from unittest.mock import Mock, patch

import pytest
import requests

from app.services.media.drop import DropClient, DropSignupError
from app.services.servers import check_drop


def _response(status=200, body=None):
    response = Mock(status_code=status)
    response.json.return_value = body if body is not None else {}
    if status >= 400:
        response.raise_for_status.side_effect = requests.HTTPError(
            f"{status} Error", response=response
        )
    return response


def _client(signup=None):
    client = DropClient.__new__(DropClient)
    signup = signup or _response(body={"id": "drop-user-1"})

    def post(path, **_kwargs):
        if path == "/api/v1/admin/auth/invitation":
            return _response(body={"id": "invite-1"})
        if signup.status_code >= 400:
            signup.raise_for_status()
        return signup

    client.post = Mock(side_effect=post)
    return client


def test_create_user_uses_the_admin_auth_invitation_path():
    client = _client()

    assert client.create_user("sam-drop", "Password1", "sam@example.com") == (
        "drop-user-1"
    )

    invitation_call, signup_call = client.post.call_args_list
    assert invitation_call.args == ("/api/v1/admin/auth/invitation",)
    assert signup_call.args == ("/api/v1/auth/signup/simple",)
    assert signup_call.kwargs["json"]["invitation"] == "invite-1"


def test_invitation_expiry_is_a_valid_iso_date():
    client = _client()

    client.create_user("sam-drop", "Password1", "sam@example.com")

    expires = client.post.call_args_list[0].kwargs["json"]["expires"]
    assert not expires.endswith("Z")
    assert datetime.fromisoformat(expires).tzinfo is not None


def test_password_is_sent_unchanged():
    client = _client()

    client.create_user("sam-drop", "Password1", "sam@example.com")

    assert client.post.call_args_list[1].kwargs["json"]["password"] == "Password1"


def test_rejected_sign_up_raises_drop_reason():
    signup = _response(400, {"message": "password must be at least length 14"})
    client = _client(signup=signup)

    with pytest.raises(DropSignupError, match="at least length 14"):
        client.create_user("sam-drop", "Password1", "sam@example.com")


def test_forbidden_sign_up_raises_permission_error():
    client = _client(signup=_response(403))

    with pytest.raises(PermissionError, match="Simple Authentication"):
        client.create_user("sam-drop", "Password1", "sam@example.com")


def test_join_shows_drop_reason_to_the_user(app):
    client = DropClient.__new__(DropClient)
    client.server_id = 1
    client.create_user = Mock(
        side_effect=DropSignupError("username must be at least length 5")
    )

    with (
        app.app_context(),
        patch("app.services.media.drop.is_invite_valid", return_value=(True, "")),
    ):
        ok, message = client._do_join(
            "sam", "Password1", "Password1", "sam@example.com", "CODE"
        )

    assert not ok
    assert "username must be at least length 5" in message


@pytest.mark.parametrize(("status", "ok"), [(200, True), (403, False)])
def test_connection_check_needs_user_read_acl(app, status, ok):
    with (
        app.app_context(),
        patch(
            "app.services.servers.requests.get", return_value=_response(status, [])
        ) as get,
    ):
        result_ok, _message = check_drop("http://drop.local/", "tok")

    assert result_ok is ok
    assert get.call_args.args == ("http://drop.local/api/v1/admin/users",)
