"""Tests for the recently added media widget (#1046 and #940)."""

import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.models import Library, MediaServer
from app.services.media.audiobookshelf import AudiobookshelfClient
from app.services.media.jellyfin import JellyfinClient
from app.services.media.komga import KomgaClient
from app.services.media.plex import PlexClient
from app.services.media.utils import library_name_selected, newest_first
from app.services.wizard_widgets import (
    process_widget_placeholders,
    widget_library_names,
)


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


def test_library_name_selected_ignores_case_and_accepts_none():
    assert library_name_selected("Movies", None)
    assert library_name_selected("Movies", {"movies"})
    assert library_name_selected("TV Shows", ["tv shows"])
    assert not library_name_selected("Anime", {"Movies"})


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


def test_plex_recent_items_use_only_selected_libraries(monkeypatch):
    client = _plex_client(monkeypatch, _plex_sections())

    items = client.get_recent_items(limit=6, library_names={"movies", "Unknown"})

    assert [item["title"] for item in items] == ["movie-new", "movie-mid"]


# ─── Jellyfin and Emby ──────────────────────────────────────────────────────


def _jellyfin_item(item_id, created):
    return {
        "Id": item_id,
        "Name": item_id,
        "Type": "Movie",
        "DateCreated": created,
        "ImageTags": {"Primary": "tag"},
    }


def _jellyfin_client(monkeypatch, get):
    return _fake_client(
        JellyfinClient,
        monkeypatch,
        url="http://jellyfin.local",
        token="token",
        get=get,
        generate_image_proxy_url=lambda url: url,
    )


def test_jellyfin_without_filter_uses_one_request_for_all_libraries(monkeypatch):
    get = MagicMock(
        return_value=_json_response(
            {"Items": [_jellyfin_item("a", "2024-01-02T00:00:00.0000000Z")]}
        )
    )
    client = _jellyfin_client(monkeypatch, get)

    items = client.get_recent_items(limit=6)

    assert [item["title"] for item in items] == ["a"]
    get.assert_called_once()
    assert "ParentId" not in get.call_args.kwargs["params"]


def test_jellyfin_merges_selected_libraries_newest_first(monkeypatch):
    folders = {
        "Items": [
            {"Id": "anime", "Name": "Anime"},
            {"Id": "movies", "Name": "Movies"},
            {"Id": "music", "Name": "Music"},
        ]
    }
    by_parent = {
        "anime": [_jellyfin_item("anime-old", "2023-01-01T00:00:00.0000000Z")],
        "movies": [
            _jellyfin_item("movie-new", "2024-05-01T00:00:00.0000000Z"),
            _jellyfin_item("movie-mid", "2024-02-01T00:00:00.0000000Z"),
        ],
    }

    def get(path, params=None):
        if path == "/Library/MediaFolders":
            return _json_response(folders)
        return _json_response({"Items": by_parent[(params or {})["ParentId"]]})

    client = _jellyfin_client(monkeypatch, get)

    items = client.get_recent_items(limit=2, library_names={"ANIME", "movies"})

    assert [item["title"] for item in items] == ["movie-new", "movie-mid"]


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
    only_a = client.get_recent_items(limit=2, library_names={"audiobooks"})
    assert [item["title"] for item in only_a] == ["a-old"]


# ─── Komga ──────────────────────────────────────────────────────────────────


def test_komga_keeps_only_books_from_selected_libraries(monkeypatch):
    books = {
        "content": [
            {"id": "1", "libraryId": "manga", "metadata": {"title": "Manga 1"}},
            {"id": "2", "libraryId": "comics", "metadata": {"title": "Comic 1"}},
            {"id": "3", "libraryId": "manga", "metadata": {"title": "Manga 2"}},
        ]
    }
    get = MagicMock(return_value=_json_response(books))
    client = _fake_client(
        KomgaClient,
        monkeypatch,
        url="http://komga.local",
        get=get,
        libraries=lambda: {"manga": "Manga", "comics": "Comics"},
        generate_image_proxy_url=lambda url: url,
    )

    items = client.get_recent_items(limit=6, library_names={"manga"})

    assert [item["title"] for item in items] == ["Manga 1", "Manga 2"]
    assert "size=100" in get.call_args.args[0]


# ─── Widget ─────────────────────────────────────────────────────────────────


def _server_with_libraries(session, libraries):
    server = MediaServer(name="Plex", server_type="plex", url="http://plex")
    session.add(server)
    session.flush()
    for index, (name, enabled) in enumerate(libraries):
        session.add(
            Library(external_id=str(index), name=name, enabled=enabled, server=server)
        )
    session.commit()
    return server


def test_widget_library_names_default_to_enabled_libraries(session):
    server = _server_with_libraries(session, [("Movies", True), ("Home Videos", False)])

    assert widget_library_names(server) == {"Movies"}
    assert widget_library_names(server, "") == {"Movies"}


def test_widget_library_names_use_the_libraries_argument(session):
    server = _server_with_libraries(session, [("Movies", True)])

    assert widget_library_names(server, " Movies, TV Shows ,") == {
        "Movies",
        "TV Shows",
    }


def test_widget_library_names_allow_all_without_a_library_list(session):
    server = _server_with_libraries(session, [])

    assert widget_library_names(server) is None


def test_widget_passes_libraries_and_limit_to_the_client(session):
    server = _server_with_libraries(session, [("Movies", True)])
    media_client = MagicMock()
    media_client.get_recent_items.return_value = [
        {"title": "Dune", "thumb": "/image-proxy?dune"}
    ]

    with patch(
        "app.services.wizard_widgets.get_media_client", return_value=media_client
    ):
        html = process_widget_placeholders(
            '{{ widget:recently_added_media libraries="Movies, TV Shows" limit=12 }}',
            server.server_type,
        )

    media_client.get_recent_items.assert_called_once_with(
        limit=12, library_names={"Movies", "TV Shows"}
    )
    assert "/image-proxy?dune" in html


def test_wizard_step_editor_offers_libraries_argument():
    template = (
        Path(__file__).parents[1]
        / "app"
        / "templates"
        / "modals"
        / "wizard-step-form.html"
    ).read_text(encoding="utf-8")

    assert 'widget:recently_added_media libraries="" limit=6' in template
