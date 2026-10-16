"""Page where users type an invite code (wizarrrr/wizarr#1208).

GET /join shows a form for the code. A valid code goes to the normal
invite flow at /j/<code>. POST /join stays the legacy Plex route.
"""

from datetime import UTC, datetime, timedelta

import pytest

from app.extensions import db
from app.models import Invitation


@pytest.fixture
def invitations(app, session):
    """A valid, an expired and a used invitation."""
    with app.app_context():
        db.session.add_all(
            [
                Invitation(code="VALID12345", used=False, unlimited=False),
                Invitation(
                    code="EXPIRED123",
                    used=False,
                    unlimited=False,
                    expires=datetime.now(UTC) - timedelta(days=1),
                ),
                Invitation(code="USEDCODE12", used=True, unlimited=False),
            ]
        )
        db.session.commit()


def test_join_page_shows_code_form(client):
    resp = client.get("/join")

    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert 'action="/join"' in html
    assert 'method="get"' in html
    assert 'name="code"' in html
    assert "aria-invalid" not in html


@pytest.mark.parametrize("typed", ["VALID12345", "  valid12345 "])
def test_valid_code_opens_the_invite_flow(client, invitations, typed):
    resp = client.get("/join", query_string={"code": typed})

    assert resp.status_code == 302
    assert resp.headers["Location"].lower() == "/j/valid12345"


@pytest.mark.parametrize(
    ("code", "error"),
    [
        ("UNKNOWN123", "Invalid code"),
        ("EXPIRED123", "Invitation has expired."),
        ("USEDCODE12", "Invitation has already been used."),
        ("ABC", "Invalid code length"),
    ],
)
def test_bad_code_shows_the_normal_error(client, invitations, code, error):
    resp = client.get("/join", query_string={"code": code})

    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert error in html
    assert f'value="{code}"' in html
    assert 'aria-describedby="code-error"' in html


def test_blank_code_shows_the_empty_form(client):
    resp = client.get("/join", query_string={"code": "   "})

    assert resp.status_code == 200
    assert "aria-invalid" not in resp.get_data(as_text=True)


def test_post_join_stays_the_legacy_plex_route(client, invitations):
    resp = client.post("/join", data={"code": "UNKNOWN123"})

    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    # The legacy route shows the Plex sign-in page with the error.
    assert 'id="plex-oauth-error"' in html
    assert "Invalid code" in html
