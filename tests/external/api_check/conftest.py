"""Fixtures for the wizard API-check tests.

The gate only applies after an invitation is accepted, so most of these build a
post-invite world: a media server, a post-invite step carrying a gate, an
accepted invitation, and the ``wizard_access`` session that marks acceptance.
"""

import pytest

from app.extensions import db
from app.models import AdminAccount, Invitation, MediaServer, User, WizardStep
from app.services.ldap.encryption import encrypt_credential
from tests.external.api_check.mock_api_server import MockApiServer

INVITE_CODE = "GATECODE1"
USERNAME = "gated-user"
EMAIL = "gated-user@example.com"
SERVER_TYPE = "jellyfin"
API_SECRET = "gate-signing-secret"


@pytest.fixture(autouse=True)
def _reset_in_process_cooldowns():
    """Clear the gate's in-process cooldown map between tests.

    It is keyed by ``scope:step_id``, and SQLite reuses row ids after the
    ``session`` fixture empties ``wizard_step`` - so without this, one test's
    cooldown lands on the next test's freshly numbered step.
    """
    from app.services.wizard_api_check import gate

    gate._IN_PROCESS_CALLS.clear()
    yield
    gate._IN_PROCESS_CALLS.clear()


@pytest.fixture
def mock_api():
    with MockApiServer() as server:
        yield server


@pytest.fixture
def signed_mock_api():
    with MockApiServer(hmac_secret=API_SECRET) as server:
        yield server


def api_check_blob(url, **overrides):
    blob = {
        "version": 1,
        "enabled": True,
        "method": "GET",
        "url": url,
        "auth_header": "",
        "api_key_enc": "",
        "sign_requests": False,
        "expect_status": [200],
        "interval_seconds": 5,
        "timeout_seconds": 5,
        "max_poll_seconds": 600,
    }
    blob.update(overrides)
    return blob


@pytest.fixture
def wizard_world(app, session):
    """A media server, an accepted invitation and its user."""
    with app.app_context():
        server = MediaServer(
            name="Gate Test Server",
            server_type=SERVER_TYPE,
            url="http://127.0.0.1:8096",
            api_key="unused",
        )
        db.session.add(server)
        db.session.flush()

        invitation = Invitation(code=INVITE_CODE, used=True, unlimited=False)
        user = User(
            token="tok-gate",
            username=USERNAME,
            email=EMAIL,
            code=INVITE_CODE,
            server_id=server.id,
        )
        db.session.add_all([invitation, user])
        db.session.flush()
        invitation.users.append(user)
        invitation.servers.append(server)
        db.session.commit()

        yield {"server": server, "invitation": invitation, "user": user}


@pytest.fixture
def make_step(app, wizard_world):
    """Create post-invite wizard steps, optionally carrying a gate."""
    created = []

    def _make(
        position,
        *,
        api_check=None,
        markdown="# Step\n\n{{ widget:api_check }}",
        category="post_invite",
    ):
        with app.app_context():
            step = WizardStep(
                server_type=SERVER_TYPE,
                category=category,
                position=position,
                title=f"Step {position}",
                markdown=markdown,
                api_check=api_check,
            )
            db.session.add(step)
            db.session.commit()
            created.append(step.id)
            return step.id

    yield _make


@pytest.fixture
def gated_step(make_step, mock_api):
    """A single post-invite step gated on the mock API."""
    return make_step(0, api_check=api_check_blob(mock_api.path("/check")))


@pytest.fixture
def accepted_client(client):
    """A client whose session says the invitation has been accepted."""
    with client.session_transaction() as sess:
        sess["wizard_access"] = INVITE_CODE
    return client


@pytest.fixture
def admin_client(client, app, wizard_world):
    """A logged-in admin, who is exempt from gating."""
    with app.app_context():
        if not AdminAccount.query.filter_by(username="gateadmin").first():
            admin = AdminAccount(username="gateadmin")
            admin.set_password("GatePass123!")
            db.session.add(admin)
            db.session.commit()
    client.post("/login", data={"username": "gateadmin", "password": "GatePass123!"})
    return client


@pytest.fixture
def signed_blob_factory():
    def _factory(url, **overrides):
        return api_check_blob(
            url,
            sign_requests=True,
            api_key_enc=encrypt_credential(API_SECRET),
            **overrides,
        )

    return _factory
