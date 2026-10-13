"""
Plex content restrictions set on an invitation (#309, #588).

An admin sets label and rating filters for movies, TV and music on the invite.
When the user accepts it, Wizarr sends the filters to plex.tv with the share.
All plexapi and plex.tv calls are fakes.
"""

import hashlib
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from flask_migrate import downgrade, upgrade
from plexapi.myplex import MyPlexAccount
from sqlalchemy import create_engine, text
from werkzeug.datastructures import MultiDict

from app import create_app
from app.config import BaseConfig
from app.extensions import db
from app.models import AdminAccount, ApiKey, Invitation, MediaServer, Settings
from app.services.invites import create_invite
from app.services.media import plex as plex_module
from app.services.media.plex import PlexClient, PlexInvitationError
from app.services.plex_restrictions import (
    PlexRestrictions,
    form_fields_from_api,
)

REVISION = "20261013_plex_invite_restrictions"
MACHINE_ID = "machine-1"


def _server(server_type: str = "plex", name: str = "Plex") -> MediaServer:
    server = MediaServer(
        name=name,
        server_type=server_type,
        url=f"http://{server_type}.local",
        api_key="key",
        verified=True,
    )
    db.session.add(server)
    db.session.commit()
    return server


def _form(server: MediaServer, **fields: str | list[str]) -> MultiDict:
    return MultiDict([("server_ids", str(server.id)), *fields.items()])


# ─── Form values ────────────────────────────────────────────────────────────


def test_form_values_become_plexapi_filters():
    form = MultiDict(
        [
            ("plex_movies_exclude_labels", " private, kids-hidden ,,private"),
            ("plex_movies_allow_ratings", "G, PG"),
            ("plex_television_allow_labels", "family"),
            ("plex_television_exclude_ratings", "TV-MA"),
            ("plex_music_exclude_labels", "explicit"),
        ]
    )

    restrictions = PlexRestrictions.from_form(form)

    assert restrictions.movies == {
        "label!": ["private", "kids-hidden"],
        "contentRating": ["G", "PG"],
    }
    assert restrictions.television == {
        "label": ["family"],
        "contentRating!": ["TV-MA"],
    }
    assert restrictions.music == {"label!": ["explicit"]}


def test_music_takes_labels_only():
    # Plex has no rating filter for music libraries.
    form = MultiDict([("plex_music_allow_ratings", "G")])

    assert not PlexRestrictions.from_form(form)


def test_two_plex_servers_on_one_invite_combine_their_values():
    form = MultiDict(
        [
            ("plex_movies_exclude_labels", ""),
            ("plex_movies_exclude_labels", "private"),
            ("plex_movies_exclude_labels", "private, adults"),
        ]
    )

    restrictions = PlexRestrictions.from_form(form)

    assert restrictions.movies == {"label!": ["private", "adults"]}


def test_empty_form_has_no_restrictions():
    restrictions = PlexRestrictions.from_form(MultiDict())

    assert not restrictions
    assert restrictions.plexapi_kwargs() == {
        "filterMovies": {},
        "filterTelevision": {},
        "filterMusic": {},
    }


def test_api_object_becomes_form_fields():
    fields = form_fields_from_api(
        {
            "movies": {"exclude_labels": ["private"], "allow_ratings": ["G", "PG"]},
            "music": {"allow_labels": ["family"]},
        }
    )

    assert fields == {
        "plex_movies_exclude_labels": ["private"],
        "plex_movies_allow_ratings": ["G", "PG"],
        "plex_music_allow_labels": ["family"],
    }


@pytest.mark.parametrize(
    "payload",
    [
        {"photos": {"exclude_labels": ["x"]}},
        {"music": {"allow_ratings": ["G"]}},
        {"movies": {"max_rating": "PG"}},
        {"movies": ["private"]},
        ["private"],
    ],
)
def test_api_object_rejects_unknown_values(payload):
    with pytest.raises(ValueError):
        form_fields_from_api(payload)


def test_api_object_can_be_absent():
    assert form_fields_from_api(None) == {}


# ─── Invite creation ────────────────────────────────────────────────────────


def test_create_invite_stores_the_restrictions(session):
    server = _server()

    invite = create_invite(
        _form(
            server,
            plex_movies_exclude_labels="private",
            plex_television_allow_ratings="TV-Y, TV-G",
            plex_music_allow_labels="family",
        )
    )

    db.session.refresh(invite)
    assert invite.plex_filter_movies == {"label!": ["private"]}
    assert invite.plex_filter_television == {"contentRating": ["TV-Y", "TV-G"]}
    assert invite.plex_filter_music == {"label": ["family"]}


def test_create_invite_without_restrictions_stores_none(session):
    invite = create_invite(_form(_server()))

    assert invite.plex_filter_movies is None
    assert invite.plex_filter_television is None
    assert invite.plex_filter_music is None


def test_create_invite_ignores_restrictions_without_a_plex_server(session):
    server = _server("jellyfin", "Jellyfin")

    invite = create_invite(_form(server, plex_movies_exclude_labels="private"))

    assert invite.plex_filter_movies is None


# ─── Invite acceptance ──────────────────────────────────────────────────────


def _plex_client(row: MediaServer) -> tuple[PlexClient, Mock]:
    client = PlexClient(media_server=row)
    admin = Mock()
    client._admin = admin
    client._server = SimpleNamespace(machineIdentifier=MACHINE_ID)
    return client, admin


def _invite(server: MediaServer, *, plex_home: bool = False, **filters) -> str:
    invite = Invitation(code="PLEXRS", plex_home=plex_home, **filters)
    invite.servers.append(server)
    db.session.add(invite)
    db.session.commit()
    return invite.code


@pytest.fixture
def plex_row(session):
    return _server()


@pytest.fixture
def accept(plex_row, monkeypatch):
    """Run _invite_user with a Plex client whose plexapi account is a Mock."""
    client, admin = _plex_client(plex_row)
    monkeypatch.setattr(plex_module, "get_client_for_media_server", lambda _: client)

    def run(code: str) -> Mock:
        plex_module._invite_user("friend@example.com", code, 1, plex_row)
        return admin

    return SimpleNamespace(run=run, client=client, admin=admin)


def test_friend_invite_sends_the_restrictions(plex_row, accept):
    code = _invite(
        plex_row,
        plex_filter_movies={"label!": ["private", "kids-hidden"]},
        plex_filter_television={"contentRating": ["TV-Y", "TV-G"]},
        plex_filter_music={"label": ["family"]},
    )

    admin = accept.run(code)

    kwargs = admin.inviteFriend.call_args.kwargs
    assert kwargs["filterMovies"] == {"label!": ["private", "kids-hidden"]}
    assert kwargs["filterTelevision"] == {"contentRating": ["TV-Y", "TV-G"]}
    assert kwargs["filterMusic"] == {"label": ["family"]}
    admin.createExistingUser.assert_not_called()


def test_home_invite_sends_the_restrictions(plex_row, accept):
    code = _invite(plex_row, plex_home=True, plex_filter_movies={"label!": ["private"]})

    admin = accept.run(code)

    kwargs = admin.createExistingUser.call_args.kwargs
    assert kwargs["filterMovies"] == {"label!": ["private"]}
    assert kwargs["filterTelevision"] == {}
    assert kwargs["filterMusic"] == {}
    admin.inviteFriend.assert_not_called()


def test_invite_without_restrictions_sends_empty_filters(plex_row, accept):
    admin = accept.run(_invite(plex_row))

    kwargs = admin.inviteFriend.call_args.kwargs
    assert kwargs["filterMovies"] == {}
    assert kwargs["filterTelevision"] == {}
    assert kwargs["filterMusic"] == {}


def test_existing_share_gets_the_restrictions_last(plex_row, accept, monkeypatch):
    """The share update calls clear the filters, so the filters come after them."""
    code = _invite(plex_row, plex_filter_movies={"label!": ["private"]})
    calls: list[str] = []
    accept.admin.inviteFriend.side_effect = PlexInvitationError(
        "You're already sharing this server with friend@example.com"
    )
    monkeypatch.setattr(
        accept.client, "update_user_libraries", lambda *_: calls.append("libraries")
    )
    monkeypatch.setattr(
        accept.client,
        "update_user_permissions",
        lambda *_: calls.append("permissions"),
    )
    accept.admin.updateFriend.side_effect = lambda *_, **__: calls.append("filters")

    admin = accept.run(code)

    assert calls == ["libraries", "permissions", "filters"]
    assert admin.updateFriend.call_args.args == (
        "friend@example.com",
        accept.client.server,
    )
    assert admin.updateFriend.call_args.kwargs == {
        "filterMovies": {"label!": ["private"]},
        "filterTelevision": {},
        "filterMusic": {},
    }


def test_existing_share_without_restrictions_skips_the_filter_call(
    plex_row, accept, monkeypatch
):
    code = _invite(plex_row)
    accept.admin.inviteFriend.side_effect = PlexInvitationError("already sharing")
    monkeypatch.setattr(accept.client, "update_user_libraries", lambda *_: True)
    monkeypatch.setattr(accept.client, "update_user_permissions", lambda *_: True)

    admin = accept.run(code)

    admin.updateFriend.assert_not_called()


def test_failed_filter_update_does_not_break_the_invite(plex_row):
    client, admin = _plex_client(plex_row)
    admin.updateFriend.side_effect = RuntimeError("plex.tv is down")

    ok = client.update_user_restrictions(
        "friend@example.com", PlexRestrictions(movies={"label!": ["private"]})
    )

    assert ok is False


# ─── plexapi wire format ────────────────────────────────────────────────────


def _recording_account() -> tuple[MyPlexAccount, dict]:
    """A MyPlexAccount that keeps the request instead of sending it."""
    account = MyPlexAccount.__new__(MyPlexAccount)
    sent: dict = {}
    account._session = Mock()
    account._getSectionIds = lambda *_: [101]
    account.query = lambda url, method, **kwargs: sent.update(url=url, **kwargs)
    return account, sent


def test_plexapi_puts_the_filters_in_the_share_request():
    """Pin the plex.tv format of plexapi 4.18.3 that the filters depend on."""
    account, sent = _recording_account()
    restrictions = PlexRestrictions(
        movies={"label!": ["private", "kids-hidden"], "contentRating": ["G", "PG"]},
        television={"contentRating!": ["TV-MA"]},
        music={"label": ["family"]},
    )

    account.inviteFriend(
        "friend@example.com",
        MACHINE_ID,
        sections=["Movies"],
        **restrictions.plexapi_kwargs(),
    )

    assert sent["url"] == f"https://plex.tv/api/servers/{MACHINE_ID}/shared_servers"
    settings = sent["json"]["sharing_settings"]
    assert (
        settings["filterMovies"] == "label!=private%2Ckids-hidden|contentRating=G%2CPG"
    )
    assert settings["filterTelevision"] == "contentRating!=TV-MA"
    assert settings["filterMusic"] == "label=family"


# ─── Admin form and API ─────────────────────────────────────────────────────


@pytest.fixture
def admin_client(client, session):
    admin = AdminAccount(username="admin")
    admin.set_password("password")
    db.session.add_all([admin, Settings(key="admin_username", value="admin")])
    db.session.commit()
    client.post("/login", data={"username": "admin", "password": "password"})
    return client


def test_invite_modal_shows_restrictions_for_plex_only(admin_client):
    plex = _server()
    jellyfin = _server("jellyfin", "Jellyfin")

    html = admin_client.get("/invite", headers={"HX-Request": "true"}).get_data(
        as_text=True
    )

    assert f'id="plexRestrictions{plex.id}"' in html
    assert f'id="plexRestrictions{jellyfin.id}"' not in html
    for name in (
        "plex_movies_exclude_labels",
        "plex_movies_allow_labels",
        "plex_movies_allow_ratings",
        "plex_movies_exclude_ratings",
        "plex_television_exclude_labels",
        "plex_television_allow_ratings",
        "plex_music_exclude_labels",
        "plex_music_allow_labels",
    ):
        assert f'name="{name}"' in html
    assert 'name="plex_music_allow_ratings"' not in html


def test_invite_modal_saves_the_restrictions(admin_client):
    plex = _server()

    response = admin_client.post(
        "/invite",
        data={
            "server_ids": str(plex.id),
            "expires": "never",
            "plex_movies_exclude_labels": "private",
        },
        headers={"HX-Request": "true", "HX-Current-URL": "http://wizarr.local/"},
    )

    assert response.status_code == 200
    invite = Invitation.query.one()
    assert invite.plex_filter_movies == {"label!": ["private"]}


@pytest.fixture
def api_key(session):
    admin = AdminAccount(username="api-admin")
    admin.set_password("password")
    db.session.add(admin)
    db.session.flush()
    raw_key = "plex-restrictions-key"  # test fixture, not a real credential
    db.session.add(
        ApiKey(
            name="test",
            key_hash=hashlib.sha256(raw_key.encode()).hexdigest(),
            created_by_id=admin.id,
            is_active=True,
        )
    )
    db.session.commit()
    return raw_key


def test_api_creates_an_invite_with_restrictions(client, api_key):
    plex = _server()

    response = client.post(
        "/api/invitations",
        json={
            "server_ids": [plex.id],
            "plex_restrictions": {
                "movies": {"exclude_labels": ["private"]},
                "television": {"allow_ratings": ["TV-Y", "TV-G"]},
            },
        },
        headers={"X-API-Key": api_key},
    )

    assert response.status_code == 201, response.get_json()
    invite = Invitation.query.one()
    assert invite.plex_filter_movies == {"label!": ["private"]}
    assert invite.plex_filter_television == {"contentRating": ["TV-Y", "TV-G"]}
    assert invite.plex_filter_music is None


def test_api_rejects_an_unknown_restriction(client, api_key):
    plex = _server()

    response = client.post(
        "/api/invitations",
        json={
            "server_ids": [plex.id],
            "plex_restrictions": {"music": {"allow_ratings": ["G"]}},
        },
        headers={"X-API-Key": api_key},
    )

    assert response.status_code == 400
    assert Invitation.query.count() == 0


# ─── Migration ──────────────────────────────────────────────────────────────

_COLUMNS = {"plex_filter_movies", "plex_filter_television", "plex_filter_music"}


def _migration_app(tmp_path):
    db_url = f"sqlite:///{tmp_path / 'migration.db'}"

    class Config(BaseConfig):
        TESTING = True
        SQLALCHEMY_DATABASE_URI = db_url

    return create_app(Config), create_engine(db_url)  # type: ignore[arg-type]


def _invitation_columns(engine) -> set[str]:
    with engine.connect() as conn:
        return {row[1] for row in conn.execute(text("PRAGMA table_info(invitation)"))}


def test_migration_adds_and_removes_the_columns(tmp_path):
    app, engine = _migration_app(tmp_path)
    with app.app_context():
        upgrade(revision=f"{REVISION}-1")
        assert not _COLUMNS & _invitation_columns(engine)

        upgrade(revision=REVISION)
        assert _invitation_columns(engine) >= _COLUMNS

        downgrade(revision=f"{REVISION}-1")
        assert not _COLUMNS & _invitation_columns(engine)
    engine.dispose()


def test_migration_keeps_rows_that_reference_the_invitation(tmp_path):
    """A rebuild of invitation deletes child rows through ON DELETE CASCADE."""
    app, engine = _migration_app(tmp_path)
    child_rows = text(
        "SELECT (SELECT count(*) FROM invitation_server),"
        " (SELECT count(*) FROM invitation_user),"
        " (SELECT count(*) FROM invite_library)"
    )
    with app.app_context():
        upgrade(revision=f"{REVISION}-1")
        with engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO media_server (id, name, server_type, url, verified,"
                    " allow_downloads, allow_live_tv, allow_mobile_uploads,"
                    " created_at)"
                    " VALUES (1, 'Plex', 'plex', 'http://plex', 1, 0, 0, 0,"
                    " '2026-01-01')"
                )
            )
            conn.execute(
                text(
                    "INSERT INTO library (id, external_id, name, enabled, server_id)"
                    " VALUES (1, 'L1', 'Movies', 1, 1)"
                )
            )
            conn.execute(
                text(
                    'INSERT INTO "user" (id, token, username, code, server_id)'
                    " VALUES (1, 't1', 'alice', 'INV1', 1)"
                )
            )
            conn.execute(
                text(
                    "INSERT INTO invitation (id, code, used, created)"
                    " VALUES (1, 'INV1', 0, '2026-01-01')"
                )
            )
            conn.execute(
                text(
                    "INSERT INTO invitation_server (invite_id, server_id, used)"
                    " VALUES (1, 1, 0)"
                )
            )
            conn.execute(
                text(
                    "INSERT INTO invitation_user (invite_id, user_id, used_at)"
                    " VALUES (1, 1, '2026-01-01')"
                )
            )
            conn.execute(
                text("INSERT INTO invite_library (invite_id, library_id) VALUES (1, 1)")
            )
            # A failed run can leave the temporary table of a batch rebuild.
            conn.execute(text("CREATE TABLE _alembic_tmp_invitation (id INTEGER)"))

        upgrade(revision=REVISION)
        with engine.connect() as conn:
            assert conn.execute(child_rows).one() == (1, 1, 1)
            leftover = conn.execute(
                text(
                    "SELECT name FROM sqlite_master"
                    " WHERE name = '_alembic_tmp_invitation'"
                )
            ).first()
            assert leftover is None

        # An earlier migration leaves foreign_keys off on the pooled
        # connection. A new connection has it on, as at container start.
        db.engine.dispose()
        downgrade(revision=f"{REVISION}-1")
        with engine.connect() as conn:
            assert conn.execute(child_rows).one() == (1, 1, 1)
    engine.dispose()


def test_migration_skips_a_column_that_an_admin_added_by_hand(tmp_path):
    app, engine = _migration_app(tmp_path)
    with app.app_context():
        upgrade(revision=f"{REVISION}-1")
        with engine.begin() as conn:
            conn.execute(
                text("ALTER TABLE invitation ADD COLUMN plex_filter_movies JSON")
            )

        upgrade(revision=REVISION)
        assert _invitation_columns(engine) >= _COLUMNS
        with engine.connect() as conn:
            version = conn.execute(text("SELECT version_num FROM alembic_version"))
            assert version.scalar() == REVISION
    engine.dispose()
