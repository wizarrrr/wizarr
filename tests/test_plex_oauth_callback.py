"""Plex OAuth returns the user to Wizarr instead of stranding them on plex.tv.

Sign-in happens on app.plex.tv in a second window. Without a ``forwardUrl`` the
browser has nowhere to go once Plex is done, so the user is left sitting on
Plex's own screen while the invite page waits behind it - on mobile, where the
second window is a whole tab, there is no way back at all.
"""

from pathlib import Path

PLEX_OAUTH_JS = Path(__file__).resolve().parents[1] / "app/static/js/plex-oauth.js"


def test_callback_page(client):
    # Plex forwards the browser here with no session of its own to present.
    resp = client.get("/plex/callback")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)

    # The callback carries the form it needs when the opener is gone.
    assert 'action="/join"' in html
    assert 'name="code"' in html
    assert 'name="token"' in html

    # Whether to step aside is decided by whether the window that opened us is
    # still on screen, read from the opener's own visibilityState - not from
    # the device, the window size, or the pointer type, all of which misjudge
    # cases like a touchscreen laptop.
    assert 'visibilityState === "visible"' in html
    assert "openerIsVisible()" in html
    assert "window.opener" in html

    # Closing a tab lets the browser surface whatever it likes, which is the
    # mobile failure this page exists to prevent. It only ever navigates; the
    # opener is what closes the desktop popup.
    assert "window.close()" not in html

    # If the opener redeems the invite first, the session is shared, so the
    # visible window follows it to the wizard rather than stranding the user.
    assert "goToWizard" in html
    assert "/wizard/" in html

    # The template must not reference a script that is not shipped.
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


def test_invite_page(client):
    # No code renders the invite page with an error, which is enough to get the
    # Plex sign-in markup without standing up an invitation.
    html = client.post("/join", data={}).get_data(as_text=True)

    # The regression itself: without forwardUrl the user never comes back.
    assert "forwardUrl" in html
    assert "/plex/callback" in html

    # The callback can only finish the sign-in if the pin id was left behind
    # before the browser went to Plex.
    assert "plexOAuthWrite" in html
    assert "pinId" in html

    # Both pages can end up holding the token, and an invite must not be
    # redeemed twice.
    assert 'plexOAuthClaim("opener")' in html
    assert 'claimedBy === "callback"' in html

    # On mobile the invite page is a background tab the browser may still run.
    # If it finished from there it would close the callback tab the user is
    # looking at, and the browser then surfaces some unrelated tab - observed
    # on Safari. A hidden invite page must stand down and let the callback
    # finish.
    assert 'document.visibilityState !== "visible"' in html
