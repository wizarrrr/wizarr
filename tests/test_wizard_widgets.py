from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.services.wizard_widgets import (
    ButtonWidget,
    CollectionMediaWidget,
    process_widget_placeholders,
)


def test_button_widget_resolves_context_variable_url():
    html = ButtonWidget().render(
        "jellyfin",
        _context={"external_url": "https://jellyfin.example.com"},
        url="external_url",
        text="Open Jellyfin",
    )

    assert 'href="https://jellyfin.example.com"' in html
    assert "Open Jellyfin" in html


def test_button_widget_accepts_legacy_context_keyword():
    html = ButtonWidget().render(
        "jellyfin",
        context={"external_url": "https://jellyfin.example.com"},
        url="external_url",
        text="Open Jellyfin",
    )

    assert 'href="https://jellyfin.example.com"' in html


def test_process_widget_placeholders_passes_context_to_button_widget():
    html = process_widget_placeholders(
        '{{ widget:button url="external_url" text="Open Jellyfin" }}',
        "jellyfin",
        context={"external_url": "https://jellyfin.example.com"},
    )

    assert 'href="https://jellyfin.example.com"' in html
    assert "Open Jellyfin" in html


def test_collection_widget_is_registered_and_renders_plex_posters():
    first_item = SimpleNamespace(
        title="Arrival", thumbUrl="http://plex/photo/1?token=x"
    )
    second_item = SimpleNamespace(title="Dune", thumbUrl="http://plex/photo/2?token=x")
    collection = SimpleNamespace(
        title="Sci-Fi", items=lambda: [first_item, second_item]
    )
    section = SimpleNamespace(collections=lambda: [collection])
    client = SimpleNamespace(
        server=SimpleNamespace(library=SimpleNamespace(sections=lambda: [section])),
        generate_image_proxy_url=lambda url: f"/image-proxy?source={url}",
    )
    server = SimpleNamespace(server_type="plex")
    query = MagicMock()
    query.filter_by.return_value.first.return_value = server

    with (
        patch("app.models.MediaServer.query", query),
        patch("app.services.wizard_widgets.get_media_client", return_value=client),
    ):
        html = process_widget_placeholders(
            '{{ widget:collection_media collection="sci-fi" limit=1 }}', "plex"
        )

    assert "Unknown widget" not in html
    assert "Arrival" in html
    assert "Dune" not in html
    assert "/image-proxy?source=http://plex/photo/1?token=x" in html


def test_collection_widget_rejects_missing_collection_name():
    assert CollectionMediaWidget().get_data("plex") == {"items": [], "limit": 15}


def test_wizard_step_editor_offers_collection_widget():
    template = (
        Path(__file__).parents[1]
        / "app"
        / "templates"
        / "modals"
        / "wizard-step-form.html"
    ).read_text(encoding="utf-8")

    assert "insertWidget('collection_media')" in template
    assert 'widget:collection_media collection="Collection Name" limit=15' in template
