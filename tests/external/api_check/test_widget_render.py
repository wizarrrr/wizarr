"""Rendering of the {{ widget:api_check }} status card.

The card is what the user actually sees and what drives the polling, so these
tests pin both the visible states and the HTMX contract. They also cover the
two ways admin-authored text could turn into an exploit: HTML injection, and
Jinja injection via the second template pass that ``_render`` performs.
"""

import re

import pytest

from app.services.wizard_api_check.config import normalize, public_view
from app.services.wizard_widgets import (
    API_CHECK_PLACEHOLDER_RE,
    WIDGET_REGISTRY,
    process_widget_placeholders,
)

GATED_STEP_ID = 42


def config(**overrides):
    raw = {
        "version": 1,
        "enabled": True,
        "url": "https://api.example.com/check",
        "sign_requests": False,
        "interval_seconds": 15,
        **overrides,
    }
    return normalize(raw, category=overrides.pop("category", "post_invite"))


def context(*, step_id=GATED_STEP_ID, passed=False, **overrides):
    return {
        "wizard_step_id": step_id,
        "wizard_api_check": public_view(config(**overrides)),
        "wizard_gate_passed": passed,
    }


def render(ctx=None, markdown="{{ widget:api_check }}"):
    with_ctx = context() if ctx is None else ctx
    return process_widget_placeholders(markdown, "jellyfin", context=with_ctx)


@pytest.fixture(autouse=True)
def _app_context(app):
    """The card renders through a Jinja template, so it needs an app context."""
    with app.app_context():
        yield


class TestRegistration:
    def test_widget_is_registered(self):
        assert "api_check" in WIDGET_REGISTRY

    def test_placeholder_pattern_matches_the_documented_syntax(self):
        assert API_CHECK_PLACEHOLDER_RE.search("{{ widget:api_check }}")
        assert API_CHECK_PLACEHOLDER_RE.search("text\n{{widget:api_check}}\ntext")
        assert not API_CHECK_PLACEHOLDER_RE.search("{{ widget:button }}")


class TestPendingState:
    def test_renders_a_card_bound_to_the_step(self):
        html = render()

        assert f'id="wizard-api-check-{GATED_STEP_ID}"' in html
        assert f"/wizard/api-check/{GATED_STEP_ID}" in html

    def test_polls_on_load_and_on_the_configured_interval(self):
        html = render()
        trigger = re.search(r'hx-trigger="([^"]*)"', html).group(1)

        assert "load" in trigger
        assert "every 15s" in trigger

    def test_swaps_itself_so_the_poll_timer_cannot_stack(self):
        html = render()

        assert 'hx-target="this"' in html
        assert 'hx-swap="outerHTML"' in html
        assert 'hx-swap="innerHTML"' not in html

    def test_offers_a_manual_recheck_button(self):
        html = render()

        assert "Re-check" in html

    def test_uses_a_scoped_indicator_not_the_global_overlay(self):
        html = render()
        indicator = re.search(r'hx-indicator="([^"]*)"', html).group(1)

        assert indicator != ".htmx-indicator"
        assert str(GATED_STEP_ID) in indicator

    def test_opts_out_of_the_require_interaction_unlock(self):
        """Clicking Re-check must not satisfy a separate require_interaction gate."""
        assert "data-wizard-no-unlock" in render()


class TestPassedState:
    def test_shows_success_and_stops_polling(self):
        html = render(context(passed=True))

        assert "hx-trigger" not in html

    def test_a_settled_card_carries_no_request_attributes(self):
        """HTMX defaults a trigger-less div to `click`, which would re-fire."""
        html = render(context(passed=True))

        assert "hx-get" not in html
        assert "hx-swap" not in html

    def test_success_message_is_shown(self):
        html = render(
            context(passed=True, success_message="App detected, you are good to go")
        )

        assert "App detected, you are good to go" in html

    def test_pending_message_is_shown_while_waiting(self):
        html = render(context(pending_message="Install the app, then tap Re-check"))

        assert "Install the app, then tap Re-check" in html

    def test_falls_back_to_default_copy_when_no_message_is_set(self):
        assert render(context()).strip() != ""
        assert render(context(passed=True)).strip() != ""


class TestInactiveGate:
    def test_disabled_gate_renders_nothing(self):
        html = render(context(enabled=False))

        assert "wizard-api-check" not in html

    def test_pre_invite_step_renders_nothing(self):
        html = render(context(category="pre_invite"))

        assert "wizard-api-check" not in html

    def test_signed_gate_without_a_key_renders_nothing(self):
        html = render(context(sign_requests=True, api_key_enc=""))

        assert "wizard-api-check" not in html

    def test_missing_step_id_renders_nothing(self):
        html = render(context(step_id=None))

        assert "wizard-api-check" not in html

    def test_absent_widget_context_renders_nothing(self):
        html = process_widget_placeholders(
            "{{ widget:api_check }}", "jellyfin", context={}
        )

        assert "wizard-api-check" not in html


class TestSecretsNeverReachThePage:
    def test_url_is_not_exposed(self):
        html = render(context(url="https://secret-internal.example.com/private-path"))

        assert "secret-internal.example.com" not in html
        assert "private-path" not in html

    def test_ciphertext_is_not_exposed(self):
        html = render(context(api_key_enc="ciphertext-value", sign_requests=False))

        assert "ciphertext-value" not in html

    def test_markdown_parameters_are_ignored(self):
        """An admin cannot redirect the check by editing the placeholder."""
        html = process_widget_placeholders(
            '{{ widget:api_check url="http://evil.test" interval=1 }}',
            "jellyfin",
            context=context(),
        )

        assert "evil.test" not in html
        assert "every 15s" in html


class TestInjectionHardening:
    def test_html_in_admin_messages_is_escaped(self):
        html = render(context(pending_message="<script>alert(1)</script>"))

        assert "<script>" not in html
        assert "&lt;script&gt;" in html

    def test_jinja_syntax_cannot_survive_into_the_second_template_pass(self):
        """`_render` re-parses widget output as a template with autoescape off."""
        html = render(context(pending_message="{{ config.SECRET_KEY }}"))

        assert "{{" not in html
        assert "{%" not in html

    def test_no_raw_braces_are_emitted_at_all(self):
        html = render(context(pending_message="a { b } c", success_message="{% raw %}"))

        assert "{" not in html
        assert "}" not in html

    def test_unicode_and_emoji_survive(self):
        html = render(context(pending_message="✅ 完了 🎉"))

        assert "✅ 完了 🎉" in html


class TestPlacementInMarkdown:
    def test_card_renders_where_the_placeholder_sits(self):
        html = render(markdown="# Title\n\n{{ widget:api_check }}\n\nAfter")

        assert html.index("# Title") < html.index("wizard-api-check")
        assert html.index("wizard-api-check") < html.index("After")

    def test_other_widgets_still_work_alongside_it(self):
        html = process_widget_placeholders(
            '{{ widget:button url="https://example.com" text="Go" }}\n\n{{ widget:api_check }}',
            "jellyfin",
            context=context(),
        )

        assert 'href="https://example.com"' in html
        assert "wizard-api-check" in html
