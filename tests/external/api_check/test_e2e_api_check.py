"""End-to-end browser test for the wizard API-check gate.

Drives a real Chromium against a live server and a real mock upstream, so it
covers the parts no unit test can: that HTMX actually polls, that the cooldown
surfaces in the UI, that a passing check flips the card and releases the Next
button without a page reload, and that polling then stops.
"""

import contextlib
import itertools
import multiprocessing

import pytest
from playwright.sync_api import Page, expect

# pytest-flask's live_server forks; spawn/forkserver cannot pickle the fixtures.
with contextlib.suppress(RuntimeError):
    multiprocessing.set_start_method("fork", force=True)

from app.extensions import db
from app.models import Invitation, MediaServer, User, WizardStep

_CODE_SEQ = itertools.count(1)
USERNAME = "e2e-gate-user"
EMAIL = "e2e-gate@example.com"
INTERVAL = 5
SERVER_TYPE = "jellyfin"

CARD = "div[id^='wizard-api-check-'][role='status']"
NEXT = "#wizard-next-btn"


@pytest.fixture
def gate_world(live_server, mock_api):
    """A gated post-invite step plus the accepted invitation that reaches it.

    Bound to ``live_server.app`` rather than the ``app`` fixture: another e2e
    module defines its own session-scoped ``app`` on a different SQLite file,
    and ``live_server`` binds to whichever wins, so this is the only way to be
    sure the data lands in the database the browser will actually read.
    """
    code = f"E2EGATE{next(_CODE_SEQ):03d}"
    server_app = live_server.app

    with server_app.app_context():
        # The app seeds default steps for every server type on boot; clear the
        # ones for our server so positions are ours alone.
        WizardStep.query.filter_by(
            server_type=SERVER_TYPE, category="post_invite"
        ).delete()

        server = MediaServer.query.filter_by(server_type=SERVER_TYPE).first()
        if server is None:
            server = MediaServer(
                name="E2E Gate Server",
                server_type=SERVER_TYPE,
                url="http://127.0.0.1:8096",
                api_key="unused",
            )
            db.session.add(server)
        db.session.flush()

        invitation = Invitation(code=code, used=True, unlimited=False)
        user = User(
            token=f"tok-{code}",
            username=USERNAME,
            email=EMAIL,
            code=code,
            server_id=server.id,
        )
        db.session.add_all([invitation, user])
        db.session.flush()
        invitation.users.append(user)
        invitation.servers.append(server)

        db.session.add_all(
            [
                WizardStep(
                    server_type=SERVER_TYPE,
                    category="post_invite",
                    position=0,
                    title="Install the app",
                    markdown="# Install the app\n\n{{ widget:api_check }}",
                    api_check={
                        "version": 1,
                        "enabled": True,
                        "method": "GET",
                        "url": mock_api.path("/check"),
                        "auth_header": "",
                        "api_key_enc": "",
                        "sign_requests": False,
                        "expect_status": [200],
                        "interval_seconds": INTERVAL,
                        "timeout_seconds": 5,
                        "max_poll_seconds": 600,
                        "pending_message": "Install the app, then tap Re-check",
                        "success_message": "App detected, you are good to go",
                    },
                ),
                WizardStep(
                    server_type=SERVER_TYPE,
                    category="post_invite",
                    position=1,
                    title="All done",
                    markdown="# All done",
                ),
            ]
        )
        db.session.commit()

    yield {"code": code, "app": server_app}

    with server_app.app_context():
        WizardStep.query.filter_by(
            server_type=SERVER_TYPE, category="post_invite"
        ).delete()
        # Delete through the ORM: a bulk delete leaves invitation_user rows
        # behind, and SQLite reuses ids, so the next run collides on them.
        stale = Invitation.query.filter_by(code=code).first()
        if stale is not None:
            stale.users.clear()
            stale.servers.clear()
            db.session.delete(stale)
        for orphan in User.query.filter_by(code=code).all():
            db.session.delete(orphan)
        db.session.commit()


def _session_cookie_value(client) -> str:
    """The signed session id werkzeug issued, whatever domain it filed it under."""
    cookie = client.get_cookie("session")
    if cookie is not None:
        return cookie.value
    for (_domain, _path, name), stored in client._cookies.items():
        if name == "session":
            return stored.value
    raise AssertionError("no session cookie was issued")


@pytest.fixture
def gated_page(page: Page, live_server, gate_world):
    """A browser already holding an accepted-invitation session.

    Sessions are server-side (cachelib on disk) and live_server forks this
    process, so handing the browser the session id is enough to land it in the
    post-invite flow without replaying the whole invitation journey.
    """
    client = gate_world["app"].test_client()
    with client.session_transaction() as sess:
        sess["wizard_access"] = gate_world["code"]

    page.context.add_cookies(
        [
            {
                "name": "session",
                "value": _session_cookie_value(client),
                "url": live_server.url(),
            }
        ]
    )
    return page


def test_gate_blocks_then_releases(gated_page: Page, live_server, mock_api):
    mock_api.set_status(403)

    gated_page.goto(f"{live_server.url()}/wizard/post-wizard/0")

    # The card renders and the load trigger fires an immediate check.
    expect(gated_page.locator(CARD)).to_be_visible()
    expect(gated_page.locator(CARD)).to_contain_text(
        "Install the app, then tap Re-check"
    )
    assert mock_api.wait_for(1), "the card should check once on load"

    # Next is locked while the gate is unsatisfied.
    expect(gated_page.locator(NEXT)).to_have_attribute("aria-disabled", "true")

    # A manual re-check inside the interval is refused server-side.
    gated_page.locator(f"{CARD} button").click()
    expect(gated_page.locator(CARD)).to_contain_text("Please wait")
    assert mock_api.request_count == 1, "the cooldown must suppress the extra call"

    # Once the upstream approves, the next automatic poll flips the card.
    mock_api.set_status(200)
    expect(gated_page.locator(CARD)).to_contain_text(
        "App detected, you are good to go", timeout=(INTERVAL + 10) * 1000
    )

    # ...and releases the Next button without a page reload.
    expect(gated_page.locator(NEXT)).not_to_have_attribute("aria-disabled", "true")

    # Polling stops once it has passed.
    settled = mock_api.request_count
    gated_page.wait_for_timeout((INTERVAL + 2) * 1000)
    assert mock_api.request_count == settled, "a passed gate must stop polling"


def test_navigation_is_blocked_while_the_gate_is_locked(
    gated_page: Page, live_server, mock_api
):
    mock_api.set_status(403)

    gated_page.goto(f"{live_server.url()}/wizard/post-wizard/1")

    expect(gated_page.locator("h1")).to_contain_text("Install the app")


def test_recheck_does_not_satisfy_require_interaction(
    gated_page: Page, live_server, mock_api, gate_world
):
    """The card's own button is marked so it cannot unlock Next by itself."""
    mock_api.set_status(403)
    with gate_world["app"].app_context():
        step = WizardStep.query.filter_by(server_type=SERVER_TYPE, position=0).first()
        step.require_interaction = True
        db.session.commit()

    gated_page.goto(f"{live_server.url()}/wizard/post-wizard/0")
    expect(gated_page.locator(CARD)).to_be_visible()

    gated_page.locator(f"{CARD} button").click()
    gated_page.wait_for_timeout(500)

    expect(gated_page.locator(NEXT)).to_have_attribute("aria-disabled", "true")
