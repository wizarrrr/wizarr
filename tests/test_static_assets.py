"""Tests for static file versioning, caching, compression and layouts."""

import gzip
import hashlib
import re
from pathlib import Path

import pytest
from flask import url_for

from app.static_assets import IMMUTABLE_MAX_AGE, StaticFileHashes

STATIC_DIR = Path(__file__).resolve().parents[1] / "app" / "static"


def _expected_hash(relative_path: str) -> str:
    content = (STATIC_DIR / relative_path).read_bytes()
    return hashlib.sha256(content).hexdigest()[:12]


def _versioned_url(app, filename: str) -> str:
    with app.test_request_context():
        return url_for("static", filename=filename, v="dev")


def test_static_url_uses_content_hash(app):
    url = _versioned_url(app, "js/wizard-steps.js")

    assert url == f"/static/js/wizard-steps.js?v={_expected_hash('js/wizard-steps.js')}"


def test_static_url_without_file_keeps_given_version(app):
    url = _versioned_url(app, "js/does-not-exist.js")

    assert url == "/static/js/does-not-exist.js?v=dev"


def test_versioned_static_request_is_immutable(app, client):
    response = client.get(_versioned_url(app, "js/wizard-steps.js"))

    assert response.status_code == 200
    cache_control = response.cache_control
    assert cache_control.public is True
    assert cache_control.immutable is True
    assert cache_control.max_age == IMMUTABLE_MAX_AGE
    assert cache_control.no_cache is None


def test_static_request_without_version_revalidates(client):
    response = client.get("/static/js/wizard-steps.js")

    assert response.status_code == 200
    assert response.cache_control.no_cache is True
    assert response.cache_control.immutable is False


def test_static_request_with_old_version_revalidates(client):
    response = client.get("/static/js/wizard-steps.js?v=000000000000")

    assert response.status_code == 200
    assert response.cache_control.no_cache is True
    assert not response.cache_control.max_age


def test_static_request_does_not_touch_session(admin_client):
    # The client has a session cookie, but a static response must not save the
    # session or set the cookie again.
    response = admin_client.get("/static/js/wizard-steps.js")

    assert response.status_code == 200
    assert "Set-Cookie" not in response.headers
    assert "cookie" not in response.headers.get("Vary", "").lower()


def test_page_request_still_uses_session(admin_client):
    response = admin_client.get("/admin")

    assert response.status_code == 200
    assert "cookie" in response.headers.get("Vary", "").lower()


@pytest.mark.parametrize(
    ("filename", "mimetypes"),
    [
        ("js/wizard-steps.js", {"text/javascript", "application/javascript"}),
        ("css/tiny-mde.min.css", {"text/css"}),
        # The type of manifest.json depends on the Python version.
        ("manifest.json", {"application/json", "application/manifest+json"}),
    ],
)
def test_static_text_files_are_compressed(app, client, filename, mimetypes):
    response = client.get(
        _versioned_url(app, filename), headers={"Accept-Encoding": "gzip"}
    )

    assert response.status_code == 200
    assert response.mimetype in mimetypes
    assert response.headers["Content-Encoding"] == "gzip"
    assert "accept-encoding" in response.headers["Vary"].lower()
    assert gzip.decompress(response.data) == (STATIC_DIR / filename).read_bytes()


def test_static_images_are_not_compressed(client):
    response = client.get(
        "/static/wizarr-logo.png", headers={"Accept-Encoding": "gzip"}
    )

    assert response.status_code == 200
    assert "Content-Encoding" not in response.headers


def test_html_responses_are_not_compressed(client):
    # HTML responses contain CSRF tokens (BREACH attack), so never compress them.
    response = client.get("/login", headers={"Accept-Encoding": "gzip, br"})

    assert response.mimetype == "text/html"
    assert "Content-Encoding" not in response.headers


def test_compressed_static_response_supports_revalidation(client):
    first = client.get(
        "/static/js/wizard-steps.js", headers={"Accept-Encoding": "gzip"}
    )
    etag = first.headers["ETag"]

    second = client.get(
        "/static/js/wizard-steps.js",
        headers={"Accept-Encoding": "gzip", "If-None-Match": etag},
    )

    assert second.status_code == 304


def test_static_hash_follows_file_changes(tmp_path):
    target = tmp_path / "app.js"
    target.write_text("one")
    hashes = StaticFileHashes(str(tmp_path))

    first = hashes.get("app.js", check_changes=True)
    target.write_text("two, longer")
    second = hashes.get("app.js", check_changes=True)

    assert first != second
    assert second == hashlib.sha256(b"two, longer").hexdigest()[:12]
    assert hashes.get("../outside.js") is None
    assert hashes.get("missing.js") is None


def test_public_page_does_not_load_admin_libraries(client):
    body = client.get("/login").get_data(as_text=True)

    for asset in (
        "tiny-mde.min.js",
        "tiny-mde.min.css",
        "init-tinymde.js",
        "sortable.min.js",
        "animate.min.css",
        "bowser.min.js",
    ):
        assert asset not in body
    assert "in-app-escape.js" in body
    assert "inapp-spy.min.js" in body
    # The public wizard needs wizard-steps.js for the interaction gating.
    assert "wizard-steps.js" in body
    htmx_tag = re.search(
        r'<script\b[^>]*\bsrc="/static/js/vendor/htmx\.min\.js[^>]*>', body
    )
    assert htmx_tag is not None
    assert re.search(r"\bdefer\b", htmx_tag.group(0))


def test_admin_layout_loads_editor_libraries(admin_client):
    body = admin_client.get("/admin").get_data(as_text=True)

    for asset in (
        "tiny-mde.min.js",
        "tiny-mde.min.css",
        "init-tinymde.js",
        "sortable.min.js",
    ):
        assert asset in body
    assert "in-app-escape.js" not in body
    assert "bowser.min.js" not in body
    # The hidden hover prefetches are gone.
    assert 'hx-trigger="hover once"' not in body
    assert "onmouseenter" not in body


def test_full_settings_page_loads_editor_libraries(admin_client):
    # /settings can load as a full page, and its wizard tab needs the editor.
    body = admin_client.get("/settings/").get_data(as_text=True)

    assert "sortable.min.js" in body
    assert "tiny-mde.min.js" in body


def test_settings_page_in_admin_layout_does_not_reload_editor(admin_client):
    body = admin_client.get("/settings/", headers={"HX-Request": "true"}).get_data(
        as_text=True
    )

    assert "sortable.min.js" not in body
    assert "in-app-escape.js" not in body
