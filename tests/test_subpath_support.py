from unittest.mock import patch

import pytest

from app.extensions import db
from app.models import AdminAccount, Invitation, MediaServer, Settings


@pytest.fixture
def subpath_app(app):
    original_root = app.config["APPLICATION_ROOT"]
    app.config["APPLICATION_ROOT"] = "/wizarr"
    yield app
    app.config["APPLICATION_ROOT"] = original_root


def test_root_redirects_to_prefixed_setup(subpath_app, client, session):

    response = client.get("/wizarr/")

    assert response.status_code == 302
    assert response.headers["Location"] == "/wizarr/setup/"


def test_root_redirects_to_prefixed_admin(subpath_app, client, session):
    db.session.add(Settings(key="admin_username", value="admin"))
    db.session.commit()

    response = client.get("/wizarr/")

    assert response.status_code == 302
    assert response.headers["Location"] == "/wizarr/admin"


def test_setup_redirects_to_prefixed_admin(subpath_app, client, session):
    response = client.post(
        "/wizarr/setup/",
        headers={"X-Forwarded-Prefix": "/"},
        data={
            "username": "admin",
            "password": "Password1",
            "confirm": "Password1",
        },
    )

    assert response.status_code == 302
    assert response.headers["Location"] == "/wizarr/admin"

    dashboard = client.get("/wizarr/admin")
    html = dashboard.get_data(as_text=True)

    assert dashboard.status_code == 200
    assert 'href="/wizarr/static/css/main.css' in html
    assert 'hx-get="/wizarr/home"' in html
    assert "/wizarr/wizarr/static" not in html
    assert 'hx-get="/home"' not in html

    home = client.get("/wizarr/home", headers={"HX-Request": "true"})
    home_html = home.get_data(as_text=True)

    assert home.status_code == 200
    assert 'hx-get="/wizarr/now-playing-cards"' in home_html
    assert 'hx-get="/wizarr/accepted-invites-card"' in home_html
    assert 'hx-get="/wizarr/server-health-card"' in home_html
    assert "htmx.ajax('GET', '/wizarr/invite'" in home_html

    invites = client.get("/wizarr/invites", headers={"HX-Request": "true"})
    invites_html = invites.get_data(as_text=True)

    assert invites.status_code == 200
    assert 'hx-post="/wizarr/invite/table"' in invites_html
    assert "htmx.ajax('GET', \"/wizarr/invite\"" in invites_html
    assert '"/wizarr/j/INVITE_CODE"' in invites_html
    assert 'hx-post="/invite/table"' not in invites_html

    users = client.get("/wizarr/users", headers={"HX-Request": "true"})
    users_html = users.get_data(as_text=True)

    assert users.status_code == 200
    assert 'hx-get="/wizarr/users/table"' in users_html
    assert 'hx-get="/wizarr/hx/users/sync"' in users_html
    assert 'hx-get="/wizarr/expired-users/table"' in users_html
    assert 'hx-post="/wizarr/users/link"' in users_html
    assert 'hx-post="/wizarr/users/unlink"' in users_html
    assert 'hx-post="/wizarr/users/bulk-delete"' in users_html
    assert 'const url = "/wizarr/users/table"' in users_html
    assert 'hx-get="/users/table"' not in users_html

    pwa_registration = client.get("/wizarr/static/js/pwa-registration.js")
    service_worker = client.get("/wizarr/static/sw.js")
    manifest = client.get("/wizarr/static/manifest.json").get_json()

    assert pwa_registration.status_code == 200
    assert "new URL('../sw.js', registrationScript.src)" in pwa_registration.text
    assert "register('/static/sw.js'" not in pwa_registration.text
    assert service_worker.status_code == 200
    assert "'/static/" not in service_worker.text
    assert manifest["start_url"] == "../"
    assert manifest["scope"] == "../"
    assert all(not icon["src"].startswith("/") for icon in manifest["icons"])


def test_created_invite_link_uses_browser_origin_and_subpath(
    subpath_app, client, session
):
    admin = AdminAccount(username="admin")
    admin.set_password("Password1")
    server = MediaServer(
        name="Test Server",
        server_type="jellyfin",
        url="http://jellyfin.local",
        api_key="test-key",
    )
    db.session.add_all([admin, server])
    db.session.commit()

    client.post(
        "/wizarr/login",
        data={"username": "admin", "password": "Password1"},
    )

    invitation = Invitation(code="PUBLIC123", used=False, unlimited=True)
    with patch("app.blueprints.admin.routes.create_invite", return_value=invitation):
        response = client.post(
            "/wizarr/invite",
            headers={
                "HX-Request": "true",
                "HX-Current-URL": "https://example.com/wizarr/admin#invites",
            },
            data={"server_ids": str(server.id)},
        )

    assert response.status_code == 200
    assert 'value="https://example.com/wizarr/j/PUBLIC123"' in response.text


def test_auth_and_profile_templates_use_prefixed_routes(
    subpath_app, client, session
):
    admin = AdminAccount(username="admin")
    admin.set_password("Password1")
    db.session.add(admin)
    db.session.commit()

    login = client.get("/wizarr/login")
    assert login.status_code == 200
    assert 'fetch("/wizarr/webauthn/authenticate/begin"' in login.text
    assert 'fetch("/webauthn/authenticate/begin"' not in login.text

    client.post(
        "/wizarr/login",
        data={"username": "admin", "password": "Password1"},
    )
    profile = client.get(
        "/wizarr/profile",
        headers={"HX-Request": "true"},
    )

    assert profile.status_code == 200
    assert 'hx-post="/wizarr/profile/change-password"' in profile.text
    assert 'hx-get="/wizarr/webauthn/add-form"' in profile.text
    assert 'hx-get="/wizarr/webauthn/list"' in profile.text
