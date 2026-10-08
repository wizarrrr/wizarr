"""
With CF_ACCESS_TEAM_DOMAIN and CF_ACCESS_AUD set, admin access needs a valid
Cloudflare Access token in Cf-Access-Jwt-Assertion on every request. A session
cookie alone, a token for another app, an expired or forged token, or a request
that never went through Access must not reach the admin pages.
"""

import datetime
import hashlib
from types import SimpleNamespace

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from app.extensions import db
from app.models import AdminAccount, ApiKey
from app.services import cloudflare_access

TEAM = "example.cloudflareaccess.com"
AUD = "test-audience-tag"
ADMIN_PAGE = "/settings/general"


def _key():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


SIGNING_KEY = _key()
OTHER_KEY = _key()


def _token(key=SIGNING_KEY, **overrides):
    now = datetime.datetime.now(datetime.UTC)
    claims = {
        "aud": [AUD],
        "iss": f"https://{TEAM}",
        "email": "admin@example.com",
        "iat": now,
        "exp": now + datetime.timedelta(minutes=10),
    }
    claims.update(overrides)
    claims = {k: v for k, v in claims.items() if v is not None}
    return jwt.encode(claims, key, algorithm="RS256", headers={"kid": "k1"})


def _headers(token):
    return {cloudflare_access.JWT_HEADER: token, "HX-Request": "true"}


@pytest.fixture
def access_mode(monkeypatch):
    """Turn Access mode on, with the team's key set served from memory."""
    monkeypatch.setenv("CF_ACCESS_TEAM_DOMAIN", f"https://{TEAM}/")
    monkeypatch.setenv("CF_ACCESS_AUD", AUD)
    stub = SimpleNamespace(
        get_signing_key_from_jwt=lambda _token: SimpleNamespace(
            key=SIGNING_KEY.public_key()
        )
    )
    monkeypatch.setattr(cloudflare_access, "_jwks_client", lambda _team: stub)


def test_disabled_by_default(monkeypatch):
    monkeypatch.delenv("CF_ACCESS_TEAM_DOMAIN", raising=False)
    monkeypatch.delenv("CF_ACCESS_AUD", raising=False)
    assert cloudflare_access.enabled() is False


def test_one_setting_alone_does_not_enable_it(monkeypatch):
    monkeypatch.setenv("CF_ACCESS_TEAM_DOMAIN", TEAM)
    monkeypatch.delenv("CF_ACCESS_AUD", raising=False)
    assert cloudflare_access.enabled() is False


def test_valid_token_logs_in_and_reaches_admin(client, session, access_mode):
    token = _token()
    login = client.get("/login", headers=_headers(token))
    assert login.status_code == 302

    page = client.get(ADMIN_PAGE, headers=_headers(token))
    assert page.status_code == 200


def test_session_without_token_is_not_admin(client, session, access_mode):
    """A request that skipped Access can't reuse an admin's session cookie."""
    client.get("/login", headers=_headers(_token()))

    page = client.get(ADMIN_PAGE, headers={"HX-Request": "true"})
    assert page.status_code in {302, 401, 403}
    assert page.status_code != 200


def test_login_without_token_is_refused(client, session, access_mode):
    assert client.get("/login").status_code == 403
    assert client.get(ADMIN_PAGE).status_code == 302


@pytest.mark.parametrize(
    "token",
    [
        pytest.param(_token(aud=["another-app"]), id="wrong audience"),
        pytest.param(
            _token(iss="https://other.cloudflareaccess.com"), id="wrong issuer"
        ),
        pytest.param(
            _token(
                exp=datetime.datetime.now(datetime.UTC) - datetime.timedelta(minutes=1)
            ),
            id="expired",
        ),
        pytest.param(_token(key=OTHER_KEY), id="forged signature"),
        pytest.param(_token(exp=None), id="no expiry"),
        pytest.param("not-a-jwt", id="garbage"),
    ],
)
def test_bad_tokens_are_refused(client, session, access_mode, token):
    assert client.get("/login", headers=_headers(token)).status_code == 403
    assert client.get(ADMIN_PAGE, headers=_headers(token)).status_code != 200


def test_access_mode_overrides_disable_builtin_auth(
    client, session, access_mode, monkeypatch
):
    monkeypatch.setenv("DISABLE_BUILTIN_AUTH", "true")
    assert client.get("/login").status_code == 403


def test_key_fetch_failure_refuses_admin(client, session, access_mode, monkeypatch):
    def unreachable(_token):
        raise jwt.PyJWKClientConnectionError("certs endpoint unreachable")

    stub = SimpleNamespace(get_signing_key_from_jwt=unreachable)
    monkeypatch.setattr(cloudflare_access, "_jwks_client", lambda _team: stub)
    assert client.get("/login", headers=_headers(_token())).status_code == 403


def test_public_paths_need_no_token(client, session, access_mode):
    assert client.get("/health").status_code == 200


def test_api_keys_work_without_a_token(client, session, access_mode):
    admin = AdminAccount(username="keyowner")
    admin.set_password("TestPass123")
    db.session.add(admin)
    db.session.commit()
    raw_key = "cf-access-test-key"
    db.session.add(
        ApiKey(
            name="Test",
            key_hash=hashlib.sha256(raw_key.encode()).hexdigest(),
            created_by_id=admin.id,
            is_active=True,
        )
    )
    db.session.commit()

    assert client.get("/api/status", headers={"X-API-Key": raw_key}).status_code == 200
    assert client.get("/api/status").status_code == 401


def test_without_access_mode_disable_builtin_auth_still_works(
    client, session, monkeypatch
):
    monkeypatch.delenv("CF_ACCESS_TEAM_DOMAIN", raising=False)
    monkeypatch.delenv("CF_ACCESS_AUD", raising=False)
    monkeypatch.setenv("DISABLE_BUILTIN_AUTH", "true")
    assert client.get("/login").status_code == 302
    assert client.get(ADMIN_PAGE, headers={"HX-Request": "true"}).status_code == 200
