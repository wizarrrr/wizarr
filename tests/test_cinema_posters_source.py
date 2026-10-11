"""
/cinema-posters takes its posters from the server picked by the
cinema_posters_source setting: the first server (the default), the servers on
the visitor's invite, or one chosen server. Invite mode must never fall back to
a server the visitor wasn't invited to.
"""

import datetime

import pytest

from app.extensions import db
from app.models import AdminAccount, Invitation, MediaServer, Settings


class PosterClient:
    def __init__(self, server):
        self.server = server

    def get_movie_posters(self, limit=80):
        return [f"poster-from-{self.server.name}"]


class NoPosterClient:
    pass


@pytest.fixture(autouse=True)
def clear_poster_cache(app):
    app.config.pop("POSTER_CACHE", None)
    yield
    app.config.pop("POSTER_CACHE", None)


@pytest.fixture
def contacted(monkeypatch):
    """Names of the servers the endpoint asked for posters."""
    calls = []

    def fake_client(server):
        calls.append(server.name)
        if server.server_type == "audiobookshelf":
            return NoPosterClient()
        return PosterClient(server)

    monkeypatch.setattr(
        "app.services.media.service.get_client_for_media_server", fake_client
    )
    return calls


def _servers():
    family = MediaServer(
        name="Family", server_type="plex", url="http://family", api_key="f"
    )
    shared = MediaServer(
        name="Shared", server_type="plex", url="http://shared", api_key="s"
    )
    books = MediaServer(
        name="Books", server_type="audiobookshelf", url="http://abs", api_key="a"
    )
    db.session.add_all([family, shared, books])
    db.session.commit()
    return family, shared, books


def _source(value):
    db.session.add(Settings(key="cinema_posters_source", value=value))
    db.session.commit()


def _invite(code, servers, expires=None):
    invitation = Invitation(code=code, used=False, expires=expires)
    invitation.servers = servers
    db.session.add(invitation)
    db.session.commit()


def _get(client, code=None):
    url = "/cinema-posters" + (f"?code={code}" if code else "")
    return client.get(url).get_json()


def test_default_is_the_first_server(client, session, contacted):
    _servers()
    assert _get(client) == ["poster-from-Family"]


def test_a_chosen_server_is_used(client, session, contacted):
    _family, shared, _books = _servers()
    _source(str(shared.id))
    assert _get(client) == ["poster-from-Shared"]


def test_a_deleted_chosen_server_falls_back_to_the_first(client, session, contacted):
    _servers()
    _source("9999")
    assert _get(client) == ["poster-from-Family"]


def test_invite_mode_uses_the_invites_server(client, session, contacted):
    _family, shared, books = _servers()
    _source("invite")
    _invite("SHARED01", [books, shared])

    # Books can't supply posters, so the next server on the invite is used
    assert _get(client, "SHARED01") == ["poster-from-Shared"]
    assert "Family" not in contacted


@pytest.mark.parametrize("code", [None, "NOSUCHCODE", "EXPIRED1"])
def test_invite_mode_without_a_valid_code_shows_nothing(
    client, session, contacted, code
):
    _family, shared, _books = _servers()
    _source("invite")
    past = datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=1)
    _invite("EXPIRED1", [shared], expires=past)

    assert _get(client, code) == []
    assert contacted == []


def test_cache_is_kept_per_server(client, session, contacted):
    _family, shared, _books = _servers()
    assert _get(client) == ["poster-from-Family"]

    _source(str(shared.id))
    assert _get(client) == ["poster-from-Shared"]


def _login(client):
    admin = AdminAccount(username="testadmin")
    admin.set_password("TestPass123")
    db.session.add(admin)
    db.session.commit()
    client.post("/login", data={"username": "testadmin", "password": "TestPass123"})


def test_settings_page_offers_and_saves_the_choice(client, session):
    _family, shared, _books = _servers()
    _login(client)

    page = client.get("/settings/general", headers={"HX-Request": "true"})
    body = page.get_data(as_text=True)
    assert 'name="cinema_posters_source"' in body
    assert 'value="invite"' in body
    assert f'value="{shared.id}"' in body

    client.post(
        "/settings/general",
        data={
            "server_name": "Wizarr",
            "expiry_action": "delete",
            "cinema_posters_source": str(shared.id),
        },
        headers={"HX-Request": "true"},
    )
    saved = Settings.query.filter_by(key="cinema_posters_source").first()
    assert saved is not None
    assert saved.value == str(shared.id)


def test_join_page_sends_its_invite_code(client, session):
    _family, shared, _books = _servers()
    _invite("JOINPAGE1", [shared])

    body = client.get("/j/JOINPAGE1").get_data(as_text=True)
    assert 'const posterCode = "JOINPAGE1";' in body
    assert "encodeURIComponent(posterCode)" in body
