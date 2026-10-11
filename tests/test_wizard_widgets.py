from app.services.wizard_widgets import ButtonWidget, process_widget_placeholders


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
