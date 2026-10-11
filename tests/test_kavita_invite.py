"""Kavita gives an invited user library access through the invite only (#1002).

/api/Account/invite takes the library ids and the age restriction. Wizarr
also sent {"userId", "libraryId"} to /api/Library/grant-access. That endpoint
takes UpdateLibraryForUserDto {username, selectedLibraries}, so Kavita
returned 400. An age rating of 0 is "Unknown" in Kavita and hides every rated
series. -1 ("Not Applicable") is no restriction.

All HTTP calls go to fakes. No test uses the network.
"""

from unittest.mock import patch

from app.models import Invitation, Library, MediaServer
from app.services.media.kavita import KavitaClient

INVITE_LINK = "http://kavita.local/registration/confirm-email?token=tok"


class _Resp:
    status_code = 200
    text = "[...]"

    def __init__(self, payload=None):
        self._payload = payload

    def json(self):
        return self._payload

    def raise_for_status(self):
        return None


def _client():
    client = KavitaClient.__new__(KavitaClient)
    client.url = "http://kavita.local"
    client.token = "api-key"
    return client


def _fake_kavita(client):
    """Answer the invite flow and record the path and body of each POST."""
    posts = []

    def post(path, json=None, **_kw):
        posts.append((path, json))
        if path == "/api/Account/invite":
            return _Resp({"emailLink": INVITE_LINK})
        return _Resp({})

    client.post = post
    client.get = lambda *_a, **_kw: _Resp([{"id": 7, "username": "sam"}])
    return posts


def test_invite_sends_libraries_and_no_age_restriction():
    client = _client()
    posts = _fake_kavita(client)

    user_id = client.create_user("sam", "Password1", "sam@example.com", ["1", "5"])

    assert user_id == "7"
    path, body = posts[0]
    assert path == "/api/Account/invite"
    assert body["libraries"] == [1, 5]
    assert body["ageRestriction"] == {"ageRating": -1, "includeUnknowns": True}


def test_join_does_not_call_grant_access(session):
    server = MediaServer(
        name="Kavita", server_type="kavita", url="http://kavita.local", api_key="k"
    )
    session.add(server)
    session.commit()
    library = Library(name="Comics", external_id="1", server_id=server.id)
    session.add_all([library, Invitation(code="KAVITA1", libraries=[library])])
    session.commit()
    client = _client()
    client.server_id = server.id
    posts = _fake_kavita(client)

    with patch("app.services.media.kavita.is_invite_valid", return_value=(True, "")):
        ok, _message = client._do_join(
            "sam", "Password1", "Password1", "sam@example.com", "KAVITA1"
        )

    assert ok
    assert [path for path, _body in posts] == [
        "/api/Account/invite",
        "/api/Account/confirm-email",
    ]
