"""Testing an Overseerr connection checks what account creation actually needs.

Provisioning runs on a background thread minutes after the invite, so when a
prerequisite is missing nobody finds out - the invited user just never gets an
account. Every prerequisite is readable anonymously, so the test button can
check the whole chain up front: the instance is Overseerr, a POST survives its CSRF
middleware, and new Plex sign-in is allowed.
"""

from contextlib import contextmanager
from unittest.mock import Mock, patch

from app.services.companions.overseerr import OverseerrClient

BASE = "https://overseerr.local"
STATUS_URL = f"{BASE}/api/v1/status"
LOGOUT_URL = f"{BASE}/api/v1/auth/logout"
SETTINGS_URL = f"{BASE}/api/v1/settings/public"


def _connection(url=BASE, provision=True):
    # spec'd so a typo'd attribute fails loudly instead of auto-vivifying.
    conn = Mock(
        spec=["url", "api_key", "name", "connection_type", "provision_plex_users"]
    )
    conn.url = url
    conn.api_key = None
    conn.name = "Overseerr"
    conn.connection_type = "overseerr"
    conn.provision_plex_users = provision
    return conn


def _resp(status=200, payload=None, text=""):
    resp = Mock(spec=["ok", "status_code", "text", "json"])
    resp.ok = 200 <= status < 300
    resp.status_code = status
    resp.text = text
    resp.json = (
        Mock(return_value=payload)
        if payload is not None
        else Mock(side_effect=ValueError("no json"))
    )
    return resp


@contextmanager
def _overseerr(status=None, logout=None, settings=None, xsrf="csrf-token-value"):
    """Stand in for the HTTP session, answering each URL the test walks."""
    status = status if status is not None else _resp(200, {"version": "3.3.0"})
    logout = logout if logout is not None else _resp(401, text="connect.sid required")
    settings = settings if settings is not None else _resp(200, {"newPlexLogin": True})

    session = Mock(spec=["get", "post", "cookies"])
    session.cookies = Mock(spec=["get"])
    session.cookies.get.return_value = xsrf
    session.get.side_effect = lambda url, **_: status if url == STATUS_URL else settings
    session.post.return_value = logout

    with patch(
        "app.services.companions.overseerr.requests.Session", return_value=session
    ):
        yield session


def test_no_url_is_informational_and_calls_nothing():
    with _overseerr() as overseerr:
        result = OverseerrClient().test_connection(_connection(url=""))

    assert result["status"] == "info_only"
    assert not overseerr.get.called
    assert not overseerr.post.called


def test_unreachable_instance_reports_the_url():
    with _overseerr() as overseerr:
        overseerr.get.side_effect = OSError("connection refused")
        result = OverseerrClient().test_connection(_connection())

    assert result["status"] == "error"
    assert BASE in result["message"]


def test_something_that_is_not_overseerr_is_not_a_pass():
    """A proxy error page or login screen answers 200 with no version."""
    with _overseerr(status=_resp(200, payload=None, text="<html>hello</html>")):
        result = OverseerrClient().test_connection(_connection())

    assert result["status"] == "error"
    assert "not with Overseerr/Jellyseerr's API" in result["message"]


def test_csrf_rejection_points_at_https():
    """The one failure that never fixes itself: Overseerr's CSRF cookies are
    Secure, so over http they are never sent back and no retry can help."""
    with _overseerr(logout=_resp(403, text='{"message":"invalid csrf token"}')):
        result = OverseerrClient().test_connection(_connection())

    assert result["status"] == "error"
    assert "https" in result["message"]


def test_csrf_probe_uses_logout_not_the_sign_in_route():
    """Posting a throwaway token to /auth/plex would prove the same thing while
    making Overseerr call plex.tv and log a failed sign-in."""
    with _overseerr() as overseerr:
        OverseerrClient().test_connection(_connection())

    (posted,) = overseerr.post.call_args[0]
    assert posted == LOGOUT_URL
    assert overseerr.post.call_args[1]["headers"]["X-XSRF-TOKEN"] == "csrf-token-value"


def test_new_plex_login_off_is_an_error_naming_the_setting():
    with _overseerr(settings=_resp(200, {"newPlexLogin": False})):
        result = OverseerrClient().test_connection(_connection())

    assert result["status"] == "error"
    assert "Enable New Plex Sign-In" in result["message"]


def test_everything_in_place_passes():
    with _overseerr() as overseerr:
        result = OverseerrClient().test_connection(_connection())

    assert result["status"] == "success"
    assert "3.3.0" in result["message"]
    # The status GET is what primes the CSRF cookie, so it has to come first.
    assert [c[0][0] for c in overseerr.get.call_args_list] == [STATUS_URL, SETTINGS_URL]


def test_provisioning_off_is_informational_not_a_pass():
    """Nothing is wrong, but nothing is being called either, and saying
    "success" would imply Wizarr creates accounts when it does not."""
    with _overseerr():
        result = OverseerrClient().test_connection(_connection(provision=False))

    assert result["status"] == "info_only"


def test_unreadable_settings_pass_but_say_so():
    """Don't fail a working instance over a setting we could not read."""
    with _overseerr(settings=_resp(403)):
        result = OverseerrClient().test_connection(_connection())

    assert result["status"] == "success"
    assert "Could not read" in result["message"]
