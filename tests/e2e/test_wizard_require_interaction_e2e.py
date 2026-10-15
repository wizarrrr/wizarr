"""End-to-end tests for wizard steps that require interaction.

On such a step, the Next button stays blocked until the user clicks a link in
the step. After that click, the Next button must open the next step. This must
work when the step opens with a full page load and when htmx swaps it in.
"""

import contextlib
import multiprocessing
from pathlib import Path

import pytest
from playwright.sync_api import Page, expect

# The live_server fixture cannot pickle its server function with "spawn".
with contextlib.suppress(RuntimeError):
    multiprocessing.set_start_method("fork", force=True)

from app.extensions import db
from app.models import Settings, WizardStep

HTMX_ASSET = Path(__file__).resolve().parents[2] / "app/static/js/vendor/htmx.min.js"

# Without the vendor assets, the browser does not load htmx and no step loads.
pytestmark = pytest.mark.skipif(
    not HTMX_ASSET.exists(),
    reason="htmx is not built. Run 'npm ci && npm run build' in app/static.",
)

# No seeded or bundled steps use this server type.
SERVER_TYPE = "gatetest"
NEXT_BUTTON = "#wizard-next-btn-desktop"
STEP_LINK = "#wizard-content .prose a"


@pytest.fixture
def gated_wizard(live_server):
    """Add three steps. Only the middle step requires interaction.

    The live_server fixture has session scope. It can use the app of another
    e2e module, so this fixture writes to the database of that app.
    """
    steps = [
        ("# First step", False),
        ("# Gated step\n\n[Open the guide](#guide)", True),
        ("# Last step", False),
    ]
    with live_server.app.app_context():
        acl = Settings.query.filter_by(key="wizard_acl_enabled").one_or_none()
        acl_created = acl is None
        if acl is None:
            acl = Settings(key="wizard_acl_enabled")
            db.session.add(acl)
        old_acl_value = acl.value
        acl.value = "false"
        for position, (markdown, require_interaction) in enumerate(steps):
            db.session.add(
                WizardStep(
                    server_type=SERVER_TYPE,
                    category="post_invite",
                    position=position,
                    markdown=markdown,
                    require_interaction=require_interaction,
                )
            )
        db.session.commit()

    yield

    with live_server.app.app_context():
        WizardStep.query.filter_by(server_type=SERVER_TYPE).delete()
        acl = Settings.query.filter_by(key="wizard_acl_enabled").one()
        if acl_created:
            db.session.delete(acl)
        else:
            acl.value = old_acl_value
        db.session.commit()


def _requests_for_last_step(page: Page) -> list[str]:
    """Record the URL of each request that loads the last step."""
    urls: list[str] = []

    def record(request):
        if f"/wizard/{SERVER_TYPE}/2" in request.url:
            urls.append(request.url)

    page.on("request", record)
    return urls


def test_next_opens_next_step_after_interaction_on_full_page_load(
    page: Page, gated_wizard, live_server
):
    page.goto(f"{live_server.url()}/wizard/{SERVER_TYPE}/1")
    expect(page.locator("#wizard-content")).to_contain_text("Gated step")
    last_step_requests = _requests_for_last_step(page)

    # Before the interaction, the Next button must not open the next step.
    page.click(NEXT_BUTTON)
    page.wait_for_load_state("networkidle")
    assert last_step_requests == []
    expect(page.locator("#wizard-content")).to_contain_text("Gated step")

    page.click(STEP_LINK)
    page.click(NEXT_BUTTON)

    expect(page.locator("#wizard-content")).to_contain_text("Last step")
    assert len(last_step_requests) == 1


def test_next_opens_next_step_after_interaction_on_htmx_swap(
    page: Page, gated_wizard, live_server
):
    page.goto(f"{live_server.url()}/wizard/{SERVER_TYPE}/0")
    expect(page.locator("#wizard-content")).to_contain_text("First step")

    page.click(NEXT_BUTTON)
    expect(page.locator("#wizard-content")).to_contain_text("Gated step")
    last_step_requests = _requests_for_last_step(page)

    page.click(STEP_LINK)
    page.click(NEXT_BUTTON)

    expect(page.locator("#wizard-content")).to_contain_text("Last step")
    assert len(last_step_requests) == 1
