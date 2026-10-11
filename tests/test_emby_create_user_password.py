"""
Emby creates a user in one call and sets the password in a second. If the
second call failed, the user used to be kept with no password and the join
reported success.
"""

from unittest.mock import Mock

import pytest
import requests

from app.services.media.emby import EmbyClient


def _client(password_error=None):
    client = EmbyClient.__new__(EmbyClient)
    created = Mock()
    created.json.return_value = {"Id": "emby-1"}

    def post(path, **_kwargs):
        if path == "/Users/New":
            return created
        if password_error:
            raise password_error
        return Mock(status_code=204)

    client.post = Mock(side_effect=post)
    client.delete_user = Mock()
    return client


def test_password_failure_removes_the_user_and_raises():
    client = _client(requests.HTTPError("500 Server Error"))

    with pytest.raises(requests.HTTPError):
        client.create_user("sam", "Password1")
    client.delete_user.assert_called_once_with("emby-1")


def test_password_success_keeps_the_user():
    client = _client()

    assert client.create_user("sam", "Password1") == "emby-1"
    client.delete_user.assert_not_called()
