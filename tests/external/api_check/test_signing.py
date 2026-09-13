"""HMAC signing of API-check requests.

Wizarr signs each call so the upstream can tell a genuine request from a forged
one. The mock server implements the verification independently, so these tests
are a real cross-check of the two sides rather than a restatement of one.
"""

import time

import pytest

from app.services.ldap.encryption import encrypt_credential
from app.services.wizard_api_check.client import build_canonical_string as app_canonical
from app.services.wizard_api_check.client import run_check
from app.services.wizard_api_check.config import normalize
from tests.external.api_check.mock_api_server import MockApiServer, sign
from tests.external.api_check.mock_api_server import (
    build_canonical_string as mock_canonical,
)

SECRET = "shared-signing-secret"


def config(url: str, **overrides):
    raw = {
        "version": 1,
        "enabled": True,
        "url": url,
        "sign_requests": True,
        "auth_header": "",
        "api_key_enc": encrypt_credential(SECRET),
        **overrides,
    }
    return normalize(raw, category="post_invite")


@pytest.fixture
def signed_api():
    with MockApiServer(hmac_secret=SECRET) as server:
        yield server


class TestCanonicalStringAgreement:
    def test_app_and_upstream_build_the_same_string(self):
        kwargs = {
            "timestamp": "1774300000",
            "nonce": "0123456789abcdef0123456789abcdef",
            "method": "GET",
            "path": "/check",
            "code": "ABC123",
            "username": "james",
            "email": "a@b.c",
        }

        assert app_canonical(**kwargs) == mock_canonical(**kwargs)

    def test_canonical_string_layout_is_pinned(self):
        """The docs and the mock server docstring quote this exact layout."""
        canonical = app_canonical(
            timestamp="1774300000",
            nonce="deadbeef",
            method="post",
            path="/pwa/status",
            code="ABC123",
            username="james",
            email="a@b.c",
        )

        assert (
            canonical
            == "v1\n1774300000\ndeadbeef\nPOST\n/pwa/status\nABC123\njames\na@b.c"
        )


class TestSignedRequestsAreAccepted:
    def test_upstream_verifies_the_signature(self, signed_api):
        outcome = run_check(
            config(signed_api.path("/check")),
            code="ABC123",
            username="james",
            email="a@b.c",
        )

        assert outcome.passed is True
        assert signed_api.last().signature_valid is True

    def test_post_requests_are_signed_too(self, signed_api):
        outcome = run_check(
            config(signed_api.path("/check"), method="POST"),
            code="ABC123",
            username="james",
            email="a@b.c",
        )

        assert outcome.passed is True
        assert signed_api.last().signature_valid is True

    def test_signing_works_without_identity_values(self, signed_api):
        outcome = run_check(config(signed_api.path("/check")), code="ABC123")

        assert outcome.passed is True
        assert signed_api.last().signature_valid is True


class TestForgeryIsRejected:
    def test_a_different_secret_fails_verification(self):
        with MockApiServer(hmac_secret="a-different-secret") as api:
            outcome = run_check(config(api.path("/check")), code="ABC123")

            assert outcome.passed is False
            assert outcome.status_code == 401
            assert api.last().signature_valid is False
            assert api.last().signature_error == "signature mismatch"

    def test_unsigned_request_is_rejected_by_a_signing_upstream(self, signed_api):
        outcome = run_check(
            config(signed_api.path("/check"), sign_requests=False), code="ABC123"
        )

        assert outcome.passed is False
        assert signed_api.last().signature_error == "missing signature headers"

    def test_signature_covers_the_identity_values(self, signed_api):
        """Swapping the code after signing must invalidate the signature."""
        run_check(config(signed_api.path("/check")), code="ABC123", username="james")
        recorded = signed_api.last()

        tampered = mock_canonical(
            timestamp=recorded.headers["X-Wizarr-Timestamp"],
            nonce=recorded.headers["X-Wizarr-Nonce"],
            method="GET",
            path="/check",
            code="SOMEONE-ELSE",
            username="james",
            email="",
        )

        assert (
            recorded.headers["X-Wizarr-Signature"] != f"sha256={sign(SECRET, tampered)}"
        )

    def test_stale_timestamps_are_refused_by_the_upstream(self):
        """Wizarr cannot enforce freshness upstream, so the upstream must."""
        with MockApiServer(hmac_secret=SECRET, clock_skew_tolerance=0) as api:
            outcome = run_check(config(api.path("/check")), code="ABC123")

            assert outcome.passed is False
            assert api.last().signature_valid is False
            assert "skew" in api.last().signature_error


class TestSignatureHeaders:
    def test_headers_are_present_and_well_formed(self, signed_api):
        run_check(config(signed_api.path("/check")), code="ABC123")
        headers = signed_api.last().headers

        assert headers["X-Wizarr-Signature"].startswith("sha256=")
        assert len(headers["X-Wizarr-Signature"]) == len("sha256=") + 64
        assert len(headers["X-Wizarr-Nonce"]) == 32
        assert abs(time.time() - int(headers["X-Wizarr-Timestamp"])) < 60

    def test_nonce_is_fresh_on_every_call(self, signed_api):
        run_check(config(signed_api.path("/check")), code="ABC123")
        first = signed_api.last().headers["X-Wizarr-Nonce"]
        run_check(config(signed_api.path("/check")), code="ABC123")
        second = signed_api.last().headers["X-Wizarr-Nonce"]

        assert first != second

    def test_no_signature_headers_when_signing_is_off(self, signed_api):
        run_check(config(signed_api.path("/check"), sign_requests=False), code="ABC123")
        headers = signed_api.last().headers

        assert "X-Wizarr-Signature" not in headers
        assert "X-Wizarr-Timestamp" not in headers
        assert "X-Wizarr-Nonce" not in headers

    def test_no_signature_headers_when_the_key_is_unusable(self, signed_api):
        run_check(
            config(signed_api.path("/check"), api_key_enc="not-a-fernet-token"),
            code="ABC123",
        )

        assert "X-Wizarr-Signature" not in signed_api.last().headers

    def test_the_secret_itself_is_never_sent_when_only_signing(self, signed_api):
        run_check(config(signed_api.path("/check")), code="ABC123")
        headers = signed_api.last().headers

        assert SECRET not in " ".join(f"{k}: {v}" for k, v in headers.items())
