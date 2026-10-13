"""End-to-end tests for the invite page /j/<code> in a real browser.

The live server runs in a separate process, so these tests cannot patch the
media clients. They check only what the browser and the app do before a media
server is contacted.
"""

import contextlib
import multiprocessing
import shutil
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from playwright.sync_api import Page, expect  # type: ignore

# The live_server fixture cannot pickle its server function with "spawn".
with contextlib.suppress(RuntimeError):
    multiprocessing.set_start_method("fork", force=True)

from app import create_app
from app.config import BaseConfig
from app.extensions import db
from app.models import (
    Invitation,
    MediaServer,
    User,
    invitation_servers,
    invitation_users,
)

# Each test process gets its own database directory. The live server is a fork
# of this process, so it uses the same file.
_E2E_DB_DIR = tempfile.mkdtemp(prefix="wizarr-e2e-")

INVITE_CODE = "E2ETEST123"


class E2ETestConfig(BaseConfig):
    TESTING = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{Path(_E2E_DB_DIR) / 'wizarr_e2e_test.db'}"


@pytest.fixture(scope="session")
def app():
    app = create_app(E2ETestConfig)  # type: ignore
    with app.app_context():
        db.create_all()
    yield app
    with app.app_context():
        db.drop_all()
        db.engine.dispose()
    shutil.rmtree(_E2E_DB_DIR, ignore_errors=True)


@pytest.fixture
def invitations(app):
    """Add a valid and an expired invitation for one Jellyfin server."""
    with app.app_context():
        server = MediaServer(
            name="Test Jellyfin Server",
            server_type="jellyfin",
            url="http://localhost:8096",
            api_key="test-api-key",
        )
        valid = Invitation(code=INVITE_CODE, duration="30", used=False)
        valid.servers = [server]
        expired = Invitation(
            code="EXPIRED123", expires=datetime.now(UTC) - timedelta(hours=1)
        )
        expired.servers = [server]
        db.session.add_all([valid, expired])
        db.session.commit()

    yield

    with app.app_context():
        db.session.execute(invitation_users.delete())
        db.session.execute(invitation_servers.delete())
        User.query.delete()
        Invitation.query.delete()
        MediaServer.query.delete()
        db.session.commit()


def _open_join_form(page: Page, live_server):
    page.goto(f"{live_server.url()}/j/{INVITE_CODE}")
    expect(page.locator("h1")).to_have_text("You've been invited!")
    expect(page.locator("#page-header")).to_contain_text("Test Jellyfin Server")
    page.click("#accept-invite-btn")
    expect(page.locator("#form-screen form")).to_be_visible()
    expect(page.locator("input[name='username']")).to_be_visible()


def test_accept_invitation_shows_the_join_form(page: Page, live_server, invitations):
    _open_join_form(page, live_server)

    for label in ("Username", "Email", "Password", "Confirm Password"):
        expect(
            page.locator("#form-screen label").filter(has_text=label).first
        ).to_be_visible()
    expect(page.locator("#form-screen form")).to_have_attribute("method", "post")
    expect(page.locator("input[name='code']")).to_have_value(INVITE_CODE)


def test_browser_blocks_an_empty_form(page: Page, live_server, invitations):
    _open_join_form(page, live_server)

    page.click("#submit-btn")

    # The required fields stop the submit, so the submit handler does not
    # disable the button and the browser stays on the invite page.
    assert page.locator("input[name='username']").evaluate(
        "el => el.validity.valueMissing"
    )
    expect(page.locator("#submit-btn")).to_be_enabled()
    assert page.url == f"{live_server.url()}/j/{INVITE_CODE}"


def test_server_rejects_mismatched_passwords(page: Page, live_server, invitations):
    _open_join_form(page, live_server)

    page.fill("input[name='username']", "testuser")
    page.fill("input[name='email']", "test@example.com")
    page.fill("input[name='password']", "Password123")
    page.fill("input[name='confirm_password']", "Different123")
    page.click("#submit-btn")

    # The form validation runs before the app contacts the media server.
    expect(page.locator("#form-screen")).to_contain_text("Passwords must match.")
    assert page.url == f"{live_server.url()}/invitation/process"


@pytest.mark.parametrize(
    ("code", "error"),
    [("EXPIRED123", "Invitation has expired."), ("NOTACODE12", "Invalid code")],
)
def test_bad_invite_code_shows_the_error(
    page: Page, live_server, invitations, code, error
):
    page.goto(f"{live_server.url()}/j/{code}")

    expect(page.locator("h1")).to_have_text("Invalid Invitation")
    expect(page.locator("p.text-red-600")).to_have_text(error)
    expect(page.locator("form")).to_have_count(0)
