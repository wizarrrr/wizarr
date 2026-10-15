"""Version API (wizarrrr/wizarr#1172).

Update monitors such as Argus read the installed version from /api/version.
"""

import hashlib

import pytest

from app.context_processors import inject_app_version
from app.models import ApiKey

RAW_KEY = "version-api-test-key"


@pytest.fixture
def api_key(session, admin_user):
    session.add(
        ApiKey(
            name="version",
            key_hash=hashlib.sha256(RAW_KEY.encode()).hexdigest(),
            created_by_id=admin_user.id,
            is_active=True,
        )
    )
    session.commit()
    return RAW_KEY


def test_version_requires_api_key(client, api_key):
    assert client.get("/api/version").status_code == 401
    assert client.get("/api/version", headers={"X-API-Key": "wrong"}).status_code == 401


def test_version_returns_app_version(client, api_key, monkeypatch):
    monkeypatch.setenv("APP_VERSION", "v2026.10.0")

    resp = client.get("/api/version", headers={"X-API-Key": api_key})

    assert resp.status_code == 200
    assert resp.get_json() == {"version": "v2026.10.0"}


def test_version_is_dev_without_app_version(client, api_key, monkeypatch):
    monkeypatch.delenv("APP_VERSION", raising=False)

    resp = client.get("/api/version", headers={"X-API-Key": api_key})

    assert resp.get_json() == {"version": "dev"}


def test_version_matches_template_version(client, api_key, monkeypatch):
    monkeypatch.setenv("APP_VERSION", "v2026.10.1")

    resp = client.get("/api/version", headers={"X-API-Key": api_key})

    assert resp.get_json()["version"] == inject_app_version()["app_version"]


def test_version_is_in_openapi_spec(client):
    spec = client.get("/api/swagger.json").get_json()

    operation = spec["paths"]["/version"]["get"]
    assert operation["operationId"] == "get_version"
    assert operation["security"] == [{"apikey": []}]
    assert "version" in spec["definitions"]["Version"]["properties"]
