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
        "<script>alert(1)</script>",
        '<img src="x" onerror="alert(1)">',
        "[Open](javascript:alert%281%29)",
        '<div hx-get="/settings/" hx-trigger="load">Test</div>',
        '<div x-init="alert(1)">Test</div>',
    ],
)
def test_step_html_removes_active_content(render_app, source):
    output = _render(SimpleNamespace(content=source), {})
    for forbidden in ("<script", "onerror=", "javascript:", "hx-get=", "x-init="):
        assert forbidden not in output


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
        "{{ settings.items() }}",
        "{{ ''.format.__call__('test') }}",
        "{% for item in 'abc' %}{{ item }}{% endfor %}",
        "{% macro repeat() %}{{ repeat() }}{% endmacro %}{{ repeat() }}",
        "{% include 'base.html' %}",
        "{% set value = 'test' %}{{ value }}",
        "{% with value = 'test' %}{{ value }}{% endwith %}",
        "{{ 'a' * 1000000000 }}",
        "{{ 2 ** 1000000000 }}",
        "{{ '%1000000000s' % 'a' }}",
    ],
)
def test_template_rejects_unsafe_operations(render_app, source):
    try:
        output = render_wizard_template(source)
    except TemplateError:
        return
    # Private attributes can resolve to an empty undefined value.
    assert output == ""


def test_template_has_only_public_display_values(render_app):
    source = "{{ server_name }} {{ settings.server_name }} {{ password }} {{ config }} {{ request }} {{ session }} {{ get_flashed_messages }}"
    output = render_wizard_template(
        source, {"server_name": "Media", "password": "secret"}
    )
    assert output.strip() == "Media Media"


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
    assert 'src="https://discord.com/widget?id=123456789&amp;theme=dark"' in output
    assert 'sandbox="allow-popups allow-same-origin allow-scripts"' in output


@pytest.mark.parametrize(
    "url",
    [
        "/settings/",
        "https://example.com",
        "javascript:alert(1)",
        "https://discord.com.evil.example/widget",
        "https://discord.com/channels/@me",
    ],
)
def test_other_embeds_cannot_load(render_app, url):
    output = _render(
        SimpleNamespace(
            content=f'<iframe src="{url}" srcdoc="<script>alert(1)</script>"></iframe>'
        ),
        {},
    )
    assert "src=" not in output
    assert "srcdoc=" not in output


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


def test_markdown_preview_removes_scripts(app, client):
    with client.session_transaction() as login_session:
        login_session["_user_id"] = "admin"
        login_session["_fresh"] = True
    response = client.post(
        "/settings/wizard/preview",
        data={"markdown": '<img src="x" onerror="alert(1)"><script>alert(1)</script>'},
    )
    assert response.status_code == 200
    assert "onerror=" not in response.get_data(as_text=True)
    assert "<script" not in response.get_data(as_text=True)
