"""Check the security boundary for stored wizard content."""

import json
from io import BytesIO, StringIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import frontmatter
import pytest
from flask import Flask
from flask_babel import Babel
from jinja2 import TemplateError

from app.blueprints.wizard.routes import _render
from app.jinja_filters import render_jinja
from app.models import MediaServer, WizardBundle, WizardStep
from app.services.wizard_presets import create_step_from_preset
from app.services.wizard_templates import render_wizard_template
from app.services.wizard_widgets import WIDGET_REGISTRY, ButtonWidget

COMMAND = "cycler.__init__.__globals__.os.popen('security-test').read()"
PAYLOAD = "{{ " + COMMAND + " }}"


@pytest.fixture
def render_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "test-secret-must-not-appear"
    Babel(app)
    with app.test_request_context("/"):
        yield app


@pytest.mark.parametrize("surface", ["body", "title", "button_text", "button_url"])
def test_stored_content_cannot_call_commands(render_app, surface):
    with patch("os.popen", return_value=StringIO("command-result")) as command:
        if surface == "body":
            output = _render(SimpleNamespace(content=PAYLOAD), {})
        elif surface == "title":
            output = render_jinja(PAYLOAD)
        elif surface == "button_text":
            output = ButtonWidget().render(
                "custom", url="https://example.com", text=PAYLOAD
            )
        else:
            source = '{{ widget:button url="' + COMMAND + '" text="Test" }}'
            output = _render(SimpleNamespace(content=source), {}, server_type="custom")
    command.assert_not_called()
    assert "command-result" not in output


@pytest.mark.parametrize(
    "source", ["{{ config.SECRET_KEY }}", "{{ settings.password }}", "{{ password }}"]
)
def test_stored_content_cannot_read_secrets(render_app, source):
    output = _render(
        SimpleNamespace(content=source), {"password": render_app.secret_key}
    )
    assert render_app.secret_key not in output


def test_widget_data_is_not_rendered_as_template_source(render_app):
    source = '{{ widget:button url="external_url" text="Open" }}'
    output = _render(
        SimpleNamespace(content=source),
        {"external_url": "https://example.com/{{ 7 * 7 }}"},
        "custom",
    )
    assert "https://example.com/49" not in output
    assert "https://example.com/{{ 7 * 7 }}" in output


@pytest.mark.parametrize(
    "source",
    [
        "<script>console.log(1)</script>",
        "<style>.note { color: red; }</style>",
        '<div style="display: flex; gap: 1rem; justify-content: center">Test</div>',
        '<div id="apps" data-platform="ios" align="center">Test</div>',
        '<button onclick="navigator.clipboard.writeText(1)">Copy</button>',
        '<iframe src="https://www.youtube.com/embed/abc" allowfullscreen></iframe>',
        '<video controls><source src="https://example.com/a.mp4"></video>',
    ],
)
def test_step_html_is_kept_as_written(render_app, source):
    # Admins write step HTML. Wizarr does not remove scripts or styles from it.
    output = _render(SimpleNamespace(content=source), {})
    assert source in output


def test_title_is_plain_text(render_app):
    output = render_jinja('<img src="x" onerror="alert(1)">')
    assert "<img" not in output


def test_third_party_bundle_import_stays_available(app, client, session):
    bundle = {
        "export_type": "bundle",
        "version": "1.0",
        "bundle": {
            "name": "Community bundle",
            "steps": [
                {
                    "server_type": "custom",
                    "position": 0,
                    "title": PAYLOAD,
                    "markdown": PAYLOAD,
                    "category": "post_invite",
                }
            ],
        },
    }
    with client.session_transaction() as login_session:
        login_session["_user_id"] = "admin"
        login_session["_fresh"] = True
    with patch("os.popen", return_value=StringIO("command-result")) as command:
        response = client.post(
            "/settings/wizard/import",
            data={
                "file": (BytesIO(json.dumps(bundle).encode()), "bundle.json"),
            },
        )
        assert response.status_code == 302
        step = WizardStep.query.filter_by(title=PAYLOAD).one()
        imported_bundle = WizardBundle.query.filter_by(name="Community bundle").one()
        preview = client.get(f"/wizard/bundle-preview/{imported_bundle.id}/0")
        assert preview.status_code == 200
        output = preview.get_data(as_text=True)
        title = render_jinja(step.title)
    command.assert_not_called()
    assert "command-result" not in output + title


@pytest.mark.parametrize(
    "source",
    [
        "{{ ().__class__.__base__.__subclasses__() }}",
        "{{ _.__globals__ }}",
        "{{ ''.format.__call__('test') }}",
        "{{ '{0.__class__}'.format(1) }}",
        "{{ ''|attr('__class__') }}",
        "{{ ''|attr('format')('{0.__class__}', 1) }}",
        "{{ cycler.__init__.__globals__ }}",
        "{{ joiner.__init__.__globals__ }}",
        "{{ namespace.__init__.__globals__ }}",
        "{{ url_for.__globals__ }}",
        "{{ gettext.__globals__ }}",
        "{{ range.__self__ }}",
        "{% macro repeat() %}{{ repeat() }}{% endmacro %}{{ repeat() }}",
        "{% for item in [1] recursive %}{{ loop([1]) }}{% endfor %}",
        "{% for a in range(100000) %}{% for b in range(100000) %}{% endfor %}{% endfor %}",
        "{% include 'base.html' %}",
        "{% import 'base.html' as base %}",
        "{% extends 'base.html' %}",
        "{{ 'a' * 1000000000 }}",
        "{{ 2 ** 1000000000 }}",
        "{{ '%1000000000s' % 'a' }}",
        "{{ '%*s' % (1000000000, 'a') }}",
        "{{ '%1000000000s'|format('a') }}",
        "{{ _('%(a)1000000000s', a='a') }}",
        "{{ gettext('%(a)1000000000s', a='a') }}",
        "{{ lipsum(100000) }}",
    ],
)
def test_template_rejects_unsafe_operations(render_app, source):
    try:
        output = render_wizard_template(source)
    except (TemplateError, RecursionError):
        return
    # Private attributes can resolve to an empty undefined value.
    assert output == ""


def test_template_has_only_public_display_values(render_app):
    source = "{{ server_name }} {{ settings.discord_id }} {{ password }} {{ config }} {{ request }} {{ session }} {{ get_flashed_messages }}"
    output = render_wizard_template(
        source, {"server_name": "Media", "discord_id": "123", "password": "secret"}
    )
    assert output.strip() == "Media 123"


@pytest.mark.parametrize(
    "key",
    [
        "admin_password",
        "server_password",
        "api_key",
        "ombi_api_key",
        "plex_token",
        "secret_key",
        "license_key",
        "session_cookie",
    ],
)
def test_template_hides_credential_settings(render_app, key):
    source = "{{ " + key + " }}{{ settings." + key + " }}{{ settings.items()|list }}"
    assert "credential" not in render_wizard_template(source, {key: "credential"})


def test_template_does_not_receive_application_objects(render_app):
    value = SimpleNamespace(secret="private")
    assert render_wizard_template("{{ server_name }}", {"server_name": value}) == ""


def test_translations_conditions_cards_and_buttons_work(render_app, monkeypatch):
    monkeypatch.setattr(
        "app.services.wizard_templates.gettext", lambda text: f"Translated {text}"
    )
    source = """{% if settings.server_name %}
|||
## {{ _("Welcome") }}

{{ server_name|upper }}

{{ widget:button url="external_url" text=_("Open") }}
|||
{% endif %}"""
    output = _render(
        SimpleNamespace(content=source),
        {"server_name": "Media", "external_url": "https://example.com"},
        "custom",
    )
    assert "Translated Welcome" in output
    assert "Translated Open" in output
    assert "MEDIA" in output
    assert 'href="https://example.com"' in output
    assert 'class="card-widget ' in output
    assert render_jinja('{{ _("Welcome") }}') == "Translated Welcome"


@pytest.mark.parametrize(
    "path",
    sorted((Path(__file__).parents[1] / "wizard_steps").glob("*/*.md")),
    ids=lambda path: f"{path.parent.name}/{path.name}",
)
def test_built_in_steps_still_render(render_app, monkeypatch, path):
    monkeypatch.setattr(
        WIDGET_REGISTRY["recently_added_media"],
        "get_data",
        lambda *args, **kwargs: {"items": []},
    )
    post = frontmatter.load(str(path))
    output = _render(
        post,
        {"external_url": "https://example.com", "server_url": "https://example.com"},
        path.parent.name,
    )
    assert "Error Loading Step" not in output
    assert "{{" not in output
    assert "<h2>" in output


def test_media_data_is_not_template_source(render_app, monkeypatch):
    monkeypatch.setattr(
        WIDGET_REGISTRY["recently_added_media"],
        "get_data",
        lambda *args, **kwargs: {
            "items": [{"title": PAYLOAD, "thumb": "https://example.com/image.jpg"}]
        },
    )
    with patch("os.popen") as command:
        output = _render(
            SimpleNamespace(content="{{ widget:recently_added_media }}"), {}, "plex"
        )
    command.assert_not_called()
    assert "https://example.com/image.jpg" in output
    assert "media-carousel-widget" in output


def test_discord_preset_keeps_restricted_embed(render_app):
    source = create_step_from_preset("discord_community", discord_id="123456789")
    output = _render(SimpleNamespace(content=source), {}, "custom")
    assert 'src="https://discord.com/widget?id=123456789&theme=dark"' in output
    assert 'sandbox="allow-popups allow-same-origin allow-scripts"' in output


@pytest.mark.parametrize(
    "url",
    [
        "javascript:alert(1)",
        "java\nscript:alert(1)",
        "data:text/html,test",
        "vbscript:msgbox(1)",
    ],
)
def test_button_rejects_executable_urls(render_app, url):
    assert "href=" not in ButtonWidget().render("custom", url=url, text="Open")


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("{% for app in ['iOS', 'Android'] %}{{ app }};{% endfor %}", "iOS;Android;"),
        ("{% set url = external_url %}{{ url }}", "https://example.com/"),
        ("{% with name = server_name %}{{ name }}{% endwith %}", "Media"),
        ("{{ external_url.rstrip('/') }}/web", "https://example.com/web"),
        ("{{ external_url|replace('https://', '') }}", "example.com/"),
        ("{{ ['a', 'b']|join(', ') }}", "a, b"),
        ("{{ _('Welcome to %(name)s', name=server_name) }}", "Welcome to Media"),
        ("{{ _('Welcome to %s') % server_name }}", "Welcome to Media"),
        ("{{ _('Save 100%') }}", "Save 100%"),
        ("{{ '%s'|format(server_name) }}", "Media"),
        ("{{ '-' * 3 }}", "---"),
        ("{% trans %}Welcome to {{ server_name }}{% endtrans %}", "Welcome to Media"),
        (
            "{% trans count=2 %}One app{% pluralize %}{{ count }} apps{% endtrans %}",
            "2 apps",
        ),
        (
            "{% macro badge(text) %}[{{ text }}]{% endmacro %}{{ badge('New') }}",
            "[New]",
        ),
        (
            "{% set ns = namespace(count=0) %}{% for i in range(3) %}"
            "{% set ns.count = ns.count + i %}{% endfor %}{{ ns.count }}",
            "3",
        ),
        ("{{ discord_id }} {{ settings.overseerr_url }}", "123 https://requests.test"),
        ("{{ url_for('static', filename='logo.png') }}", "/static/logo.png"),
    ],
)
def test_common_template_features_work(render_app, source, expected):
    context = {
        "server_name": "Media",
        "external_url": "https://example.com/",
        "discord_id": "123",
        "overseerr_url": "https://requests.test",
    }
    assert render_wizard_template(source, context) == expected


def test_button_can_use_a_setting_url(render_app):
    output = _render(
        SimpleNamespace(
            content='{{ widget:button url="overseerr_url" text="Requests" }}'
        ),
        {"overseerr_url": "https://requests.test"},
        "plex",
    )
    assert 'href="https://requests.test"' in output


def test_imported_title_is_safe_in_settings(app, client, session):
    session.add(
        MediaServer(name="Media", server_type="plex", url="https://example.com")
    )
    session.add(
        WizardStep(
            server_type="plex",
            category="post_invite",
            position=0,
            title=PAYLOAD,
            markdown="Welcome",
        )
    )
    session.commit()
    with client.session_transaction() as login_session:
        login_session["_user_id"] = "admin"
        login_session["_fresh"] = True
    with patch("os.popen") as command:
        response = client.get("/settings/wizard/", headers={"HX-Request": "true"})
    assert response.status_code == 200
    command.assert_not_called()


def test_markdown_preview_keeps_html(app, client):
    with client.session_transaction() as login_session:
        login_session["_user_id"] = "admin"
        login_session["_fresh"] = True
    source = '<div style="display: flex">Apps</div>'
    response = client.post("/settings/wizard/preview", data={"markdown": source})
    assert response.status_code == 200
    assert source in response.get_data(as_text=True)
