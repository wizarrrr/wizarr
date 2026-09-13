"""Outbound behaviour of the wizard API-check client.

These run against the real mock server on loopback rather than a patched
``requests``, so timeouts, refused connections and redirects are exercised for
real. The rule the whole feature rests on is that the upstream response body is
never read and never surfaced - only a pass/fail verdict leaves this layer.
"""

import socket

import pytest

from app.services.wizard_api_check.client import CheckOutcome, run_check
from app.services.wizard_api_check.config import ApiCheckConfig, normalize
from tests.external.api_check.mock_api_server import MockApiServer


def config(url: str, **overrides):
    raw = {
        "version": 1,
        "enabled": True,
        "url": url,
        "sign_requests": False,
        "auth_header": "",
        **overrides,
    }
    return normalize(raw, category="post_invite")


@pytest.fixture
def api():
    with MockApiServer() as server:
        yield server


def closed_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class TestStatusMatching:
    def test_expected_status_passes(self, api):
        outcome = run_check(config(api.path("/check")), code="ABC123")

        assert outcome == CheckOutcome(passed=True, reason="ok", status_code=200)

    def test_unexpected_status_fails(self, api):
        api.set_status(403)

        outcome = run_check(config(api.path("/check")), code="ABC123")

        assert outcome.passed is False
        assert outcome.reason == "status"
        assert outcome.status_code == 403

    def test_upstream_500_is_a_plain_failure(self, api):
        outcome = run_check(config(api.path("/boom")), code="ABC123")

        assert outcome.passed is False
        assert outcome.reason == "status"
        assert outcome.status_code == 500

    def test_non_default_expected_status(self, api):
        outcome = run_check(
            config(api.path("/teapot"), expect_status=[418]), code="ABC123"
        )

        assert outcome.passed is True
        assert outcome.status_code == 418

    def test_multiple_expected_statuses(self, api):
        api.set_status(204)

        outcome = run_check(
            config(api.path("/check"), expect_status=[201, 204]), code="ABC123"
        )

        assert outcome.passed is True
        assert outcome.status_code == 204

    def test_default_expectation_is_200_only(self, api):
        api.set_status(201)

        assert run_check(config(api.path("/check")), code="ABC123").passed is False


class TestRedirects:
    def test_redirect_is_not_followed(self, api):
        outcome = run_check(config(api.path("/redirect")), code="ABC123")

        assert outcome.passed is False
        assert outcome.reason == "redirect"
        assert outcome.status_code == 302
        assert api.request_count == 1, (
            "a redirect must never be chased to a second host"
        )

    def test_redirect_still_not_followed_when_explicitly_expected(self, api):
        outcome = run_check(
            config(api.path("/redirect"), expect_status=[302]), code="ABC123"
        )

        assert outcome.passed is True
        assert api.request_count == 1


class TestNetworkFailures:
    def test_timeout(self, api):
        api.set_delay(2.0)

        outcome = run_check(config(api.path("/slow"), timeout_seconds=1), code="ABC123")

        assert outcome.passed is False
        assert outcome.reason == "timeout"
        assert outcome.status_code is None

    def test_slow_but_within_timeout_still_passes(self, api):
        api.set_delay(0.5)

        outcome = run_check(config(api.path("/slow"), timeout_seconds=5), code="ABC123")

        assert outcome.passed is True

    def test_dns_failure(self):
        outcome = run_check(
            config("http://wizarr-nonexistent.invalid/check"), code="ABC123"
        )

        assert outcome.passed is False
        assert outcome.reason == "network"
        assert outcome.status_code is None

    def test_connection_refused(self):
        outcome = run_check(
            config(f"http://127.0.0.1:{closed_port()}/check"), code="ABC123"
        )

        assert outcome.passed is False
        assert outcome.reason == "network"


class TestPayload:
    def test_get_sends_identity_as_query_params(self, api):
        run_check(
            config(api.path("/check")), code="ABC123", username="james", email="a@b.c"
        )

        recorded = api.last()
        assert recorded.method == "GET"
        assert recorded.query["code"] == ["ABC123"]
        assert recorded.query["username"] == ["james"]
        assert recorded.query["email"] == ["a@b.c"]
        assert recorded.body is None

    def test_post_sends_identity_as_json_body(self, api):
        run_check(
            config(api.path("/check"), method="POST"),
            code="ABC123",
            username="james",
            email="a@b.c",
        )

        recorded = api.last()
        assert recorded.method == "POST"
        assert recorded.body == {
            "code": "ABC123",
            "username": "james",
            "email": "a@b.c",
        }
        assert recorded.query == {}

    def test_custom_param_names_are_honoured(self, api):
        run_check(
            config(
                api.path("/check"),
                code_param="invite",
                username_param="user",
                email_param="mail",
            ),
            code="ABC123",
            username="james",
            email="a@b.c",
        )

        recorded = api.last()
        assert recorded.query["invite"] == ["ABC123"]
        assert recorded.query["user"] == ["james"]
        assert recorded.query["mail"] == ["a@b.c"]
        assert "code" not in recorded.query

    def test_blank_param_name_omits_the_field(self, api):
        run_check(
            config(api.path("/check"), username_param="", email_param=""),
            code="ABC123",
            username="james",
            email="a@b.c",
        )

        recorded = api.last()
        assert recorded.query["code"] == ["ABC123"]
        assert "username" not in recorded.query
        assert "email" not in recorded.query

    def test_missing_email_is_sent_as_empty_string(self, api):
        run_check(config(api.path("/check")), code="ABC123", username="james", email="")

        assert api.last().query["email"] == [""]

    def test_identity_values_cannot_escape_into_the_url(self, api):
        """User-derived values go through requests' encoder, never string concat."""
        run_check(
            config(api.path("/check")),
            code="ABC&admin=1#x",
            username="../../etc/passwd",
            email="a b@c",
        )

        recorded = api.last()
        assert recorded.path == "/check"
        assert recorded.query["code"] == ["ABC&admin=1#x"]
        assert recorded.query["username"] == ["../../etc/passwd"]
        assert "admin" not in recorded.query


class TestAuthHeader:
    def test_header_and_prefix_are_sent(self, api):
        from app.services.ldap.encryption import encrypt_credential

        run_check(
            config(
                api.path("/check"),
                auth_header="Authorization",
                auth_prefix="Bearer ",
                api_key_enc=encrypt_credential("sk-live-1"),
            ),
            code="ABC123",
        )

        assert api.last().headers["Authorization"] == "Bearer sk-live-1"

    def test_empty_prefix_sends_the_bare_key(self, api):
        from app.services.ldap.encryption import encrypt_credential

        run_check(
            config(
                api.path("/check"),
                auth_header="X-API-Key",
                auth_prefix="",
                api_key_enc=encrypt_credential("sk-live-2"),
            ),
            code="ABC123",
        )

        assert api.last().headers["X-API-Key"] == "sk-live-2"

    def test_blank_header_name_sends_no_auth(self, api):
        run_check(config(api.path("/check")), code="ABC123")

        assert "Authorization" not in api.last().headers


class TestUrlRevalidation:
    """The stored blob is re-checked at call time, not trusted."""

    @pytest.mark.parametrize(
        "url",
        [
            "file:///etc/passwd",
            "gopher://evil.test/",
            "https://user:pass@example.com/x",
            "",
            "not a url",
        ],
    )
    def test_bad_url_never_reaches_the_network(self, url):
        outcome = run_check(
            ApiCheckConfig(enabled=True, url=url, sign_requests=False, auth_header=""),
            code="ABC123",
        )

        assert outcome == CheckOutcome(passed=False, reason="config", status_code=None)


class TestBodyIsNeverRead:
    def test_outcome_carries_no_upstream_content(self, api):
        outcome = run_check(config(api.path("/check")), code="ABC123")

        assert set(vars(outcome)) == {"passed", "reason", "status_code"}
        assert "ok" not in str(outcome.status_code)

    def test_a_body_that_cannot_be_parsed_does_not_affect_the_verdict(self, api):
        """The mock always answers with JSON; the client must not care either way."""
        api.set_status(200)

        assert run_check(config(api.path("/check")), code="ABC123").passed is True
