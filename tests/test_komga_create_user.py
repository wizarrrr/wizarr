"""Komga's web reader needs PAGE_STREAMING to load book pages.

create_user used to send only USER, plus FILE_DOWNLOAD when downloads are
allowed. Komga stores that list as the full role set (USER is display-only
on their side), so the reader stayed off until an admin enabled it.
"""

from unittest.mock import Mock

import pytest

from app.services.media.komga import KomgaClient


def _client():
    client = KomgaClient.__new__(KomgaClient)
    created = Mock()
    created.json.return_value = {"id": "komga-1"}
    client.post = Mock(return_value=created)
    return client


@pytest.mark.parametrize(
    ("allow_downloads", "roles"),
    [
        (False, ["USER", "PAGE_STREAMING"]),
        (True, ["USER", "PAGE_STREAMING", "FILE_DOWNLOAD"]),
    ],
)
def test_create_user_includes_page_streaming(allow_downloads, roles):
    client = _client()

    user_id = client.create_user(
        "unused", "secret", "reader@example.com", allow_downloads
    )

    assert user_id == "komga-1"
    client.post.assert_called_once_with(
        "/api/v2/users",
        json={
            "email": "reader@example.com",
            "password": "secret",
            "roles": roles,
        },
    )
