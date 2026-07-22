"""Plex OAuth returns the user to Wizarr instead of stranding them on plex.tv.

Sign-in happens on app.plex.tv in a second window. Without a ``forwardUrl`` the
browser has nowhere to go once Plex is done, so the user is left sitting on
Plex's own screen while the invite page waits behind it - on mobile, where the
second window is a whole tab, there is no way back at all.
"""

from pathlib import Path

PLEX_OAUTH_JS = Path(__file__).resolve().parents[1] / "app/static/js/plex-oauth.js"


def test_callback_route_is_public(client):
    """Plex forwards the browser here with no session of its own to present."""
    resp = client.get("/plex/callback")
    assert resp.status_code == 200


def test_callback_page_can_complete_the_join_on_its_own(client):
    """The callback carries the form it needs when the opener is gone."""
    html = client.get("/plex/callback").get_data(as_text=True)

    assert 'action="/join"' in html
    assert 'name="code"' in html
    assert 'name="token"' in html


def test_hands_back_only_when_the_opener_is_visible(client):
    """Whether to step aside is decided by whether the window that opened us is
    still on screen, read from the opener's own visibilityState - not from the
    device, the window size, or the pointer type, all of which misjudge cases
    like a touchscreen laptop."""
    html = client.get("/plex/callback").get_data(as_text=True)

    assert 'visibilityState === "visible"' in html
    assert "openerIsVisible()" in html
    # It must be the opener's visibility, not this window's.
    assert "window.opener" in html


def test_callback_never_closes_itself(client):
    """Closing a tab lets the browser surface whatever it likes, which is the
    mobile failure this page exists to prevent. It only ever navigates; the
    opener is what closes the desktop popup."""
    html = client.get("/plex/callback").get_data(as_text=True)

    assert "window.close()" not in html


def test_a_tab_that_loses_the_race_still_reaches_the_wizard(client):
    """If the opener redeems the invite first, the session is shared, so the
    visible window follows it to the wizard rather than stranding the user."""
    html = client.get("/plex/callback").get_data(as_text=True)

    assert "goToWizard" in html
    assert "/wizard/" in html


def test_callback_page_loads_the_shared_oauth_helpers(client):
    """Guards against the template referencing a script that is not shipped."""
    html = client.get("/plex/callback").get_data(as_text=True)

    assert "js/plex-oauth.js" in html
    assert PLEX_OAUTH_JS.exists()


def test_shared_helpers_expose_the_coordination_api():
    """The invite page and the callback page share this state via localStorage."""
    source = PLEX_OAUTH_JS.read_text()

    for helper in (
        "function plexOAuthRead",
        "function plexOAuthWrite",
        "function plexOAuthClear",
        "function plexOAuthClaim",
        "async function plexOAuthPollToken",
    ):
        assert helper in source


def test_invite_page_asks_plex_to_forward_back(client):
    """The regression itself: without forwardUrl the user never comes back."""
    # No code renders the invite page with an error, which is enough to get the
    # Plex sign-in markup without standing up an invitation.
    html = client.post("/join", data={}).get_data(as_text=True)

    assert "forwardUrl" in html
    assert "/plex/callback" in html


def test_invite_page_stashes_what_the_callback_needs(client):
    """The callback can only finish the sign-in if the pin id was left behind
    before the browser went to Plex."""
    html = client.post("/join", data={}).get_data(as_text=True)

    assert "plexOAuthWrite" in html
    assert "pinId" in html


def test_only_one_context_redeems_the_invite(client):
    """Both the invite page and the callback can end up holding the token, and
    an invite must not be redeemed twice."""
    html = client.post("/join", data={}).get_data(as_text=True)

    assert 'plexOAuthClaim("opener")' in html
    assert 'claimedBy === "callback"' in html
