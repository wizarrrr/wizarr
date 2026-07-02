from urllib.parse import parse_qs, urlsplit

import pytest

from app.models import Invitation
from app.services.external_enrollment.providers import (
    ExternalEnrollmentContext,
    append_query_params,
    build_external_enrollment_url,
    get_external_enrollment_provider,
)


def make_context() -> ExternalEnrollmentContext:
    """Create a reusable external enrollment context for URL builder tests."""
    return ExternalEnrollmentContext(
        invite_code="abc123",
        state="state-token",
        callback_url="https://wizarr.example/invitation/external/callback",
    )


def test_static_url_provider_appends_context_params():
    """Test that the static URL provider appends Wizarr invite context parameters."""
    invitation = Invitation(
        code="abc123",
        account_creation_mode="external",
        external_enrollment_provider="static_url",
        external_enrollment_url="https://idp.example/enroll",
        external_enrollment_append_context=True,
    )

    result = build_external_enrollment_url(invitation, make_context())

    parts = urlsplit(result)
    query = parse_qs(parts.query)

    assert parts.scheme == "https"
    assert parts.netloc == "idp.example"
    assert parts.path == "/enroll"
    assert query["source"] == ["wizarr"]
    assert query["invite_code"] == ["abc123"]
    assert query["state"] == ["state-token"]
    assert query["callback_url"] == [
        "https://wizarr.example/invitation/external/callback"
    ]


def test_static_url_provider_preserves_existing_query_params():
    """Test that existing provider query parameters are preserved."""
    invitation = Invitation(
        code="abc123",
        account_creation_mode="external",
        external_enrollment_provider="static_url",
        external_enrollment_url="https://idp.example/enroll?flow=family",
        external_enrollment_append_context=True,
    )

    result = build_external_enrollment_url(invitation, make_context())

    query = parse_qs(urlsplit(result).query)

    assert query["flow"] == ["family"]
    assert query["source"] == ["wizarr"]
    assert query["invite_code"] == ["abc123"]


def test_static_url_provider_can_skip_context_params():
    """Test that context parameters are not appended when disabled."""
    invitation = Invitation(
        code="abc123",
        account_creation_mode="external",
        external_enrollment_provider="static_url",
        external_enrollment_url="https://idp.example/enroll",
        external_enrollment_append_context=False,
    )

    result = build_external_enrollment_url(invitation, make_context())

    assert result == "https://idp.example/enroll"


def test_static_url_provider_requires_url():
    """Test that the static URL provider rejects missing enrollment URLs."""
    invitation = Invitation(
        code="abc123",
        account_creation_mode="external",
        external_enrollment_provider="static_url",
        external_enrollment_url=None,
        external_enrollment_append_context=True,
    )

    with pytest.raises(ValueError, match="External enrollment URL is required"):
        build_external_enrollment_url(invitation, make_context())


def test_unknown_provider_is_rejected():
    """Test that unsupported external enrollment providers are rejected."""
    with pytest.raises(ValueError, match="Unsupported external enrollment provider"):
        get_external_enrollment_provider("not-real")


def test_append_query_params_overwrites_existing_context_params():
    """Test that generated context parameters replace stale values in the URL."""
    result = append_query_params(
        "https://idp.example/enroll?source=old&flow=family",
        {
            "source": "wizarr",
            "invite_code": "abc123",
        },
    )

    query = parse_qs(urlsplit(result).query)

    assert query["source"] == ["wizarr"]
    assert query["flow"] == ["family"]
    assert query["invite_code"] == ["abc123"]
