"""Posters shown before sign-in only come from enabled libraries.

/cinema-posters and the recently added carousel are public, so a disabled
library (home video, say) must not show up there. A server that has never been
scanned has no library rows and keeps using every section.
"""

from unittest.mock import Mock

from app.models import Library, MediaServer
from app.services.media.plex import PlexClient


def _server(session, libraries=()):
    server = MediaServer(
        name="Plex", server_type="plex", url="http://plex.local", api_key="token"
    )
    session.add(server)
    session.commit()
    for i, (name, enabled) in enumerate(libraries):
        session.add(
            Library(external_id=str(i), name=name, enabled=enabled, server_id=server.id)
        )
    session.commit()
    return server


def _item(title):
    item = Mock(spec=["title", "posterUrl", "type"])
    item.title = title
    item.posterUrl = f"/library/metadata/{title}/thumb"
    item.type = "movie"
    return item


def _section(title, section_type="movie"):
    section = Mock(spec=["title", "type", "recentlyAdded"])
    section.title = title
    section.type = section_type
    section.recentlyAdded.return_value = [_item(f"{title}-item")]
    return section


def _client(server, sections):
    client = PlexClient.__new__(PlexClient)
    client.server_id = server.id
    client.url = server.url
    client._server = Mock()
    client._server.library.sections.return_value = sections
    client.generate_image_proxy_url = lambda url: url
    return client


def test_movie_posters_skip_disabled_libraries(session):
    server = _server(session, [("Movies", True), ("Home Videos", False)])
    movies, home = _section("Movies"), _section("Home Videos")

    posters = _client(server, [movies, home]).get_movie_posters(limit=10)

    assert posters == ["http://plex.local/library/metadata/Movies-item/thumb"]
    home.recentlyAdded.assert_not_called()


def test_recent_items_skip_disabled_libraries(session):
    server = _server(session, [("Movies", True), ("Home Videos", False)])
    movies, home = _section("Movies"), _section("Home Videos")

    items = _client(server, [movies, home]).get_recent_items(limit=10)

    assert [i["title"] for i in items] == ["Movies-item"]
    home.recentlyAdded.assert_not_called()


def test_library_names_match_case_insensitively(session):
    server = _server(session, [("movies", True)])

    posters = _client(server, [_section("Movies")]).get_movie_posters(limit=10)

    assert len(posters) == 1


def test_never_scanned_server_uses_every_section(session):
    server = _server(session)

    posters = _client(
        server, [_section("Movies"), _section("Home Videos")]
    ).get_movie_posters(limit=10)

    assert len(posters) == 2
