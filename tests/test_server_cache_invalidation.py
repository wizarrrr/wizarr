"""A server create, edit or delete clears the image proxy and Plex caches.

The image proxy keeps the origin and the auth headers of each server for
5 minutes. Before, a server edit did not clear them. After a URL change the
proxy did not attach the new key to the new origin, so the images of the
server failed until the TTL ended.

No test uses the network.
"""

from unittest.mock import Mock

import pytest

from app.extensions import db
from app.models import MediaServer
from app.services.image_proxy import ImageProxyService
from app.services.media import plex as plex_module
from app.services.media import service

pytestmark = pytest.mark.usefixtures("clear_media_caches")


def _server(name, url, api_key="old-key"):
    server = MediaServer(
        name=name, server_type="jellyfin", url=url, api_key=api_key, verified=True
    )
    db.session.add(server)
    db.session.commit()
    return server


def test_forget_server_drops_only_that_server(app, session):
    with app.app_context():
        edited = _server("Edited", "http://old.local")
        other = _server("Other", "http://other.local")
        assert ImageProxyService.get_server_headers(
            edited.id, "http://old.local/Items/1/Images/Primary"
        ) == {"X-MediaBrowser-Token": "old-key"}
        ImageProxyService.get_server_headers(other.id, "http://other.local/x.jpg")
        edited_session = ImageProxyService.get_session("http://old.local/a", edited.id)
        edited_session.close = Mock()
        ImageProxyService.get_session("http://other.local/a", other.id)
        ImageProxyService.cache_image(
            ImageProxyService.image_cache_key(edited.id, "http://old.local/a.jpg"),
            b"edited",
            "image/jpeg",
        )
        other_key = ImageProxyService.image_cache_key(
            other.id, "http://other.local/a.jpg"
        )
        ImageProxyService.cache_image(other_key, b"other", "image/jpeg")
        no_server_key = ImageProxyService.image_cache_key(None, "http://cdn/a.jpg")
        ImageProxyService.cache_image(no_server_key, b"cdn", "image/jpeg")

        ImageProxyService.forget_server(edited.id)

        assert edited.id not in ImageProxyService._server_header_cache
        assert edited.id not in ImageProxyService._server_url_cache
        assert ("server", edited.id) not in ImageProxyService._session_cache
        edited_session.close.assert_called_once()
        assert other.id in ImageProxyService._server_header_cache
        assert ("server", other.id) in ImageProxyService._session_cache
        assert list(ImageProxyService._image_cache) == [other_key, no_server_key]
        assert ImageProxyService._total_image_bytes == len(b"other") + len(b"cdn")


def test_invalidate_server_caches_uses_the_new_url_and_key(app, session):
    with app.app_context():
        server = _server("Edited", "http://old.local")
        ImageProxyService.get_server_headers(server.id, "http://old.local/a.jpg")
        plex_module._plex_servers[("http://plex.local", "tok")] = object()

        server.url = "http://new.local"
        server.api_key = "new-key"
        db.session.commit()
        service.invalidate_server_caches(server.id)

        assert ImageProxyService.get_server_headers(
            server.id, "http://new.local/a.jpg"
        ) == {"X-MediaBrowser-Token": "new-key"}
        # The old origin gets no credentials.
        assert (
            ImageProxyService.get_server_headers(server.id, "http://old.local/a.jpg")
            == {}
        )
        assert len(plex_module._plex_servers) == 0


def test_edit_route_clears_the_image_proxy_headers(app, admin_client, monkeypatch):
    with app.app_context():
        server = _server("Edited", "http://old.local")
        server_id = server.id
        ImageProxyService.get_server_headers(server_id, "http://old.local/a.jpg")
    assert server_id in ImageProxyService._server_header_cache

    monkeypatch.setattr(
        "app.blueprints.media_servers.routes.check_server_connection",
        lambda *_args: (True, ""),
    )
    response = admin_client.post(
        f"/settings/servers/{server_id}/edit",
        data={
            "server_name": "Edited",
            "server_type": "jellyfin",
            "server_url": "http://new.local",
            "api_key": "new-key",
        },
    )

    assert response.status_code == 302
    assert server_id not in ImageProxyService._server_header_cache
    assert server_id not in ImageProxyService._server_url_cache
    with app.app_context():
        assert ImageProxyService.get_server_headers(
            server_id, "http://new.local/a.jpg"
        ) == {"X-MediaBrowser-Token": "new-key"}
