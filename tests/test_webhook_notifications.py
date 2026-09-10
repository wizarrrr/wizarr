"""Unit tests for the generic webhook notification agent.

These tests cover the parts of app/services/notifications.py that don't
require a Flask app or DB: URL validation and payload signing/shape. The
Notification model dispatch is covered by the existing app-level tests once
the migration has been applied.
"""

import hashlib
import hmac
import json
from unittest.mock import patch

from app.services.notifications import _webhook, is_webhook_url_allowed


class TestIsWebhookUrlAllowed:
    def test_https_allowed(self):
        assert is_webhook_url_allowed("https://example.com/hook")

    def test_http_loopback_allowed(self):
        assert is_webhook_url_allowed("http://127.0.0.1:5059/hook")
        assert is_webhook_url_allowed("http://localhost:5059/hook")
        assert is_webhook_url_allowed("http://host.docker.internal:5059/hook")
        assert is_webhook_url_allowed("http://[::1]/hook")

    def test_http_non_loopback_rejected(self):
        assert not is_webhook_url_allowed("http://example.com/hook")
        assert not is_webhook_url_allowed("http://10.0.0.5/hook")

    def test_unsupported_schemes_rejected(self):
        assert not is_webhook_url_allowed("ftp://example.com/hook")
        assert not is_webhook_url_allowed("not-a-url")


class TestWebhookDispatch:
    def _captured_post(self):
        """Return a mock replacing requests.post that records its call."""
        calls = []

        class _Resp:
            status_code = 200
            text = ""

        def fake_post(url, data=None, headers=None, timeout=None):
            calls.append({"url": url, "data": data, "headers": headers})
            return _Resp()

        return calls, fake_post

    def test_signs_body_with_hmac_sha256(self):
        calls, fake_post = self._captured_post()
        secret = "s3cret"
        with patch("app.services.notifications.requests.post", fake_post):
            ok = _webhook(
                url="https://example.com/hook",
                secret=secret,
                event_type="user_joined",
                title="New User",
                message="bob joined",
                context={"user": {"username": "bob"}},
                include_password=False,
            )
        assert ok
        assert len(calls) == 1
        body = calls[0]["data"]
        expected_sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        assert calls[0]["headers"]["X-Wizarr-Signature"] == f"sha256={expected_sig}"

    def test_password_omitted_when_opt_out(self):
        calls, fake_post = self._captured_post()
        with patch("app.services.notifications.requests.post", fake_post):
            _webhook(
                url="https://example.com/hook",
                secret=None,
                event_type="user_joined",
                title="",
                message="",
                context={"user": {"username": "bob"}, "password": "hunter2"},
                include_password=False,
            )
        payload = json.loads(calls[0]["data"])
        assert "password" not in payload
        assert payload["user"]["username"] == "bob"

    def test_password_included_when_opt_in(self):
        calls, fake_post = self._captured_post()
        with patch("app.services.notifications.requests.post", fake_post):
            _webhook(
                url="https://example.com/hook",
                secret=None,
                event_type="user_joined",
                title="",
                message="",
                context={"user": {"username": "bob"}, "password": "hunter2"},
                include_password=True,
            )
        payload = json.loads(calls[0]["data"])
        assert payload["password"] == "hunter2"

    def test_http_non_loopback_refused_before_send(self):
        calls, fake_post = self._captured_post()
        with patch("app.services.notifications.requests.post", fake_post):
            ok = _webhook(
                url="http://evil.example.com/hook",
                secret="s",
                event_type="user_joined",
                title="",
                message="",
                context={"password": "hunter2"},
                include_password=True,
            )
        assert not ok
        assert calls == []  # nothing was sent

    def test_payload_has_event_and_timestamp(self):
        calls, fake_post = self._captured_post()
        with patch("app.services.notifications.requests.post", fake_post):
            _webhook(
                url="https://example.com/hook",
                secret=None,
                event_type="user_joined",
                title="New User",
                message="bob joined",
                context={},
                include_password=False,
            )
        payload = json.loads(calls[0]["data"])
        assert payload["event"] == "user_joined"
        assert "timestamp" in payload
        assert payload["title"] == "New User"
