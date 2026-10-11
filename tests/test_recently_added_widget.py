"""Tests for the recently added media widget (#1046)."""

import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.services.media.audiobookshelf import AudiobookshelfClient
from app.services.media.plex import PlexClient
from app.services.media.utils import newest_first


def _json_response(payload):
    response = MagicMock()
    response.json.return_value = payload
    return response


def _fake_client(cls, monkeypatch, **attributes):
    """Make a client without a database row, with some attributes replaced."""
    client = cls.__new__(cls)
    for name, value in attributes.items():
        monkeypatch.setattr(client, name, value, raising=False)
    return client


# ─── Shared helpers ─────────────────────────────────────────────────────────


def test_newest_first_sorts_mixed_date_formats_and_applies_limit():
    items = [
        {"title": "old", "added_at": "2023-01-01T00:00:00Z"},
        {"title": "none", "added_at": None},
        {"title": "new", "added_at": "2024-06-01T12:00:00.1234567Z"},
        {"title": "mid", "added_at": "2024-01-01T00:00:00+00:00"},
    ]

    result = newest_first(items, 3)

    assert [item["title"] for item in result] == ["new", "mid", "old"]


# ─── Plex ───────────────────────────────────────────────────────────────────


def _plex_item(title, added_at):
    return SimpleNamespace(
        title=title,
        thumb=f"/library/metadata/{title}/thumb",
        year=2024,
        type="movie",
        addedAt=added_at,
    )


def _plex_section(title, items):
    def recently_added(maxresults):
        return items[:maxresults]

    return SimpleNamespace(title=title, recentlyAdded=recently_added)


def _plex_client(monkeypatch, sections):
    return _fake_client(
        PlexClient,
        monkeypatch,
        url="http://plex.local:32400",
        _server=SimpleNamespace(library=SimpleNamespace(sections=lambda: sections)),
        _small_image_url=lambda key: key,
        generate_image_proxy_url=lambda url: f"/image-proxy?{url}",
    )


def _plex_sections():
    # plexapi gives dates without a time zone.
    day = datetime.datetime(2024, 1, 1)  # noqa: DTZ001
    anime = _plex_section(
        "Anime Movies",
        [
            _plex_item("anime-old-1", day),
            _plex_item("anime-old-2", day - datetime.timedelta(days=1)),
        ],
    )
    movies = _plex_section(
        "Movies",
        [
            _plex_item("movie-new", day + datetime.timedelta(days=30)),
            _plex_item("movie-mid", day + datetime.timedelta(days=10)),
        ],
    )
    return [anime, movies]


def test_plex_recent_items_are_the_newest_across_libraries(monkeypatch):
    client = _plex_client(monkeypatch, _plex_sections())

    items = client.get_recent_items(limit=3)

    assert [item["title"] for item in items] == [
        "movie-new",
        "movie-mid",
        "anime-old-1",
    ]


# ─── Audiobookshelf ─────────────────────────────────────────────────────────


def _abs_entity(entity_id, added_ms):
    return {
        "id": entity_id,
        "addedAt": added_ms,
        "mediaType": "book",
        "media": {"coverPath": "/cover.jpg", "metadata": {"title": entity_id}},
    }


def test_audiobookshelf_merges_libraries_newest_first(monkeypatch):
    shelves = {
        "lib-a": [_abs_entity("a-old", 1_600_000_000_000)],
        "lib-b": [_abs_entity("b-new", 1_700_000_000_000)],
    }

    def get(path):
        library_id = path.split("/")[-2]
        return _json_response(
            [{"category": "newestItems", "entities": shelves[library_id]}]
        )

    client = _fake_client(
        AudiobookshelfClient,
        monkeypatch,
        url="http://abs.local",
        get=get,
        libraries=lambda: {"lib-a": "Audiobooks", "lib-b": "Podcasts"},
        generate_image_proxy_url=lambda url: url,
    )

    assert [item["title"] for item in client.get_recent_items(limit=2)] == [
        "b-new",
        "a-old",
    ]
