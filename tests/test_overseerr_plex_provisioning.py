"""Invited Plex users get their Overseerr account made for them.

Overseerr does not import Plex users in the background - it creates them the
first time they sign in. So an invited user lands on a login screen before
anything knows who they are, and watchlist syncing has no token to work with
until they get around to it. Wizarr holds their Plex token during the invite,
which is everything that first sign-in would have supplied.
"""

from contextlib import contextmanager
from unittest.mock import Mock, patch

from app.services.companions import get_companion_client
from app.services.companions.overseerr import (
    _PROVISION_BACKOFF_SECONDS,
    OverseerrClient,
)
from app.services.ombi_client import (
    has_plex_provisioning_connections,
    provision_plex_user_on_connections,
)


def _connection(url="http://seerr.local:5055", watchlist_sync=False):
    # spec'd so a typo'd attribute fails loudly instead of auto-vivifying,
    # which is how a broken patch once passed its tests.
    conn = Mock(
        spec=[
            "url",
            "api_key",
            "name",
            "connection_type",
            "enable_watchlist_sync",
        ]
    )
    conn.url = url
    conn.api_key = None
    conn.name = "Seerr"
    conn.connection_type = "overseerr"
    conn.enable_watchlist_sync = watchlist_sync
    return conn


def _resp(status=200, text="", json=None):
    """Overseerr replies carry a body we now read, so mocks must have one."""
    resp = Mock(ok=200 <= status < 300, status_code=status, text=text)
    resp.json.return_value = {} if json is None else json
    return resp


@contextmanager
def _seerr(xsrf="csrf-token-value"):
    """Stand in for the HTTP session, handing back a primed CSRF cookie."""
    session = Mock(spec=["get", "post", "cookies"])
    session.cookies = Mock(spec=["get"])
    session.cookies.get.return_value = xsrf

    with (
        patch(
            "app.services.companions.overseerr.requests.Session",
            return_value=session,
        ),
        patch("app.services.companions.overseerr.time.sleep") as sleep,
    ):
        yield session, sleep


def test_posts_the_plex_token_to_the_login_route():
    with _seerr() as (seerr, _):
        seerr.post.return_value = _resp(200)
        result = OverseerrClient().provision_plex_user("plex-token-abc", _connection())

    assert result["status"] == "success"
    (url,) = seerr.post.call_args[0]
    assert url == "http://seerr.local:5055/api/v1/auth/plex"
    assert seerr.post.call_args[1]["json"] == {"authToken": "plex-token-abc"}


def test_sends_the_csrf_token_overseerr_handed_us():
    """Without this every POST comes back 403 "invalid csrf token", whatever the
    payload. Overseerr applies CSRF to API callers, not just browsers."""
    with _seerr(xsrf="the-expected-token") as (seerr, _):
        seerr.post.return_value = _resp(200)
        OverseerrClient().provision_plex_user("t", _connection())

    # The cookie only arrives on a response, so a GET has to come first.
    (primed_url,) = seerr.get.call_args[0]
    assert primed_url == "http://seerr.local:5055/api/v1/status"
    assert seerr.post.call_args[1]["headers"]["X-XSRF-TOKEN"] == "the-expected-token"


def test_no_csrf_header_when_the_instance_does_not_use_one():
    """CSRF protection is optional; inventing a header would be wrong."""
    with _seerr(xsrf=None) as (seerr, _):
        seerr.post.return_value = _resp(200)
        OverseerrClient().provision_plex_user("t", _connection())

    assert seerr.post.call_args[1]["headers"] == {}


def test_no_api_key_is_sent():
    """/api/v1/auth/plex is the public login route; an API key would be wrong."""
    with _seerr() as (seerr, _):
        seerr.post.return_value = _resp(200)
        OverseerrClient().provision_plex_user("plex-token-abc", _connection())

    headers = seerr.post.call_args[1]["headers"]
    assert "ApiKey" not in headers
    assert "X-Api-Key" not in headers


def test_trailing_slash_on_the_url_does_not_double_up():
    with _seerr() as (seerr, _):
        seerr.post.return_value = _resp(200)
        OverseerrClient().provision_plex_user(
            "t", _connection("http://seerr.local:5055/")
        )

    (url,) = seerr.post.call_args[0]
    assert url == "http://seerr.local:5055/api/v1/auth/plex"


def test_retries_while_the_share_is_not_visible_yet():
    """403 can mean plex.tv has not published the brand new share yet."""
    with _seerr() as (seerr, _):
        seerr.post.side_effect = [
            _resp(403, "Access denied."),
            _resp(200),
        ]
        result = OverseerrClient().provision_plex_user("t", _connection())

    assert result["status"] == "success"
    assert seerr.post.call_count == 2


def test_does_not_retry_a_csrf_rejection():
    """A CSRF 403 is the request being refused, not the user. Overseerr's CSRF
    cookies are Secure, so an http:// URL can never satisfy them and retrying
    just burns eight minutes before reporting the wrong thing."""
    with _seerr() as (seerr, _):
        seerr.post.return_value = _resp(403, '{"message":"invalid csrf token"}')
        result = OverseerrClient().provision_plex_user("t", _connection())

    assert seerr.post.call_count == 1
    assert result["status"] == "error"
    # The body has to survive into the message, or this looks like a rejected
    # user and sends the next person debugging in the wrong direction.
    assert "csrf" in result["message"].lower()


def test_keeps_retrying_for_minutes_not_seconds():
    with _seerr() as (seerr, sleep):
        seerr.post.return_value = _resp(403, "Access denied.")
        OverseerrClient().provision_plex_user("t", _connection())

    waited = sum(call[0][0] for call in sleep.call_args_list)
    assert waited >= 300, f"only retried across {waited}s"
    assert seerr.post.call_count == len(_PROVISION_BACKOFF_SECONDS) + 1


def test_gives_up_immediately_on_errors_that_will_not_fix_themselves():
    with _seerr() as (seerr, _):
        seerr.post.return_value = _resp(500, "Unable to authenticate.")
        result = OverseerrClient().provision_plex_user("t", _connection())

    assert result["status"] == "error"
    assert seerr.post.call_count == 1


def test_skipped_when_no_url_is_configured():
    """Info-only connections carry no URL and must stay a no-op."""
    with _seerr() as (seerr, _):
        result = OverseerrClient().provision_plex_user("t", _connection(url=None))

    assert result["status"] == "skipped"
    seerr.post.assert_not_called()


def test_a_companion_that_cannot_provision_is_a_no_op():
    """Ombi provisions its own way; the hook must not change its behaviour."""
    result = get_companion_client("ombi")().provision_plex_user("t", _connection())

    assert result["status"] == "not_supported"


def test_connection_failure_is_reported_not_raised():
    """A companion being down must never fail an invite the user just accepted."""
    with _seerr() as (seerr, _):
        seerr.post.side_effect = OSError("connection refused")
        result = OverseerrClient().provision_plex_user("t", _connection())

    assert result["status"] == "error"
    assert "connection refused" in result["message"]


def test_only_opted_in_connections_are_queried(app):
    """Most instances have no request system, and an existing connection that
    predates the flag must not start provisioning on upgrade."""
    with (
        app.app_context(),
        patch("app.services.ombi_client.Connection") as connection_model,
    ):
        connection_model.query.filter_by.return_value.all.return_value = []

        results = provision_plex_user_on_connections("t", server_id=7)

    assert results == []
    connection_model.query.filter_by.assert_called_once_with(
        media_server_id=7, provision_plex_users=True
    )


def test_no_background_work_when_nothing_opted_in(app):
    """Gates spawning the retry thread, so instances without a request system
    pay nothing on every invite."""
    with (
        app.app_context(),
        patch("app.services.ombi_client.Connection") as connection_model,
    ):
        connection_model.query.filter_by.return_value.count.return_value = 0

        assert has_plex_provisioning_connections(7) is False

        connection_model.query.filter_by.return_value.count.return_value = 1

        assert has_plex_provisioning_connections(7) is True


def test_both_connection_forms_offer_the_opt_in(app):
    """Connections are edited from two templates; a toggle present in only one
    is a toggle half the users cannot find."""
    from pathlib import Path

    for path in (
        "app/templates/modals/connection-form.html",
        "app/templates/settings/connections/form.html",
    ):
        body = Path(path).read_text()
        assert "provision_plex_users" in body, path
        assert "enable_watchlist_sync" in body, path


# ─── Watchlist syncing ──────────────────────────────────────────────────


def _provisioned(user_id=42, settings=None):
    """The two replies a provisioning run reads when watchlist sync is on."""
    login = _resp(200, json={"id": user_id})
    read = _resp(200, json=settings if settings is not None else {"locale": "en"})
    return login, read


def test_watchlist_sync_is_left_alone_unless_asked_for():
    """It changes a preference belonging to the user, so it stays opt-in and
    separate from merely creating the account."""
    with _seerr() as (seerr, _):
        seerr.post.return_value = _resp(200, json={"id": 42})
        result = OverseerrClient().provision_plex_user("t", _connection())

    assert result["status"] == "success"
    # Only the sign-in, no settings write.
    assert seerr.post.call_count == 1


def test_turns_on_both_watchlist_flags_for_the_new_user():
    """Overseerr leaves both unset on a new account and skips users whose flags
    are unset, so a watchlist added on day one requests nothing, silently."""
    login, read = _provisioned(user_id=42)
    with _seerr() as (seerr, _):
        seerr.post.side_effect = [login, _resp(200)]
        seerr.get.return_value = read

        result = OverseerrClient().provision_plex_user(
            "t", _connection(watchlist_sync=True)
        )

    assert result["status"] == "success"
    (url,) = seerr.post.call_args[0]
    assert url == "http://seerr.local:5055/api/v1/user/42/settings/main"
    body = seerr.post.call_args[1]["json"]
    assert body["watchlistSyncMovies"] is True
    assert body["watchlistSyncTv"] is True


def test_the_settings_write_echoes_back_what_it_read():
    """The endpoint assigns username and the regions straight from the body, so
    anything left out is blanked rather than kept."""
    login, read = _provisioned(
        settings={
            "username": "invited-user",
            "locale": "en",
            "discoverRegion": "US",
            "streamingRegion": "US",
            "originalLanguage": "en",
        }
    )
    with _seerr() as (seerr, _):
        seerr.post.side_effect = [login, _resp(200)]
        seerr.get.return_value = read

        OverseerrClient().provision_plex_user("t", _connection(watchlist_sync=True))

    body = seerr.post.call_args[1]["json"]
    assert body["username"] == "invited-user"
    assert body["discoverRegion"] == "US"
    assert body["streamingRegion"] == "US"
    assert body["originalLanguage"] == "en"


def test_a_missing_locale_is_sent_as_empty_not_null():
    """A user with no settings row yet has no locale to echo, and the column is
    NOT NULL - posting the missing value back is a 500."""
    login, read = _provisioned(settings={"username": "invited-user"})
    with _seerr() as (seerr, _):
        seerr.post.side_effect = [login, _resp(200)]
        seerr.get.return_value = read

        OverseerrClient().provision_plex_user("t", _connection(watchlist_sync=True))

    assert seerr.post.call_args[1]["json"]["locale"] == ""


def test_the_settings_write_uses_the_token_signing_in_rotated_to():
    """Signing in rotates the CSRF token; the one primed beforehand no longer
    validates and every settings write would come back 403."""
    login, read = _provisioned()
    with _seerr(xsrf="primed-token") as (seerr, _):
        seerr.post.side_effect = [login, _resp(200)]
        seerr.get.return_value = read
        seerr.cookies.get.side_effect = ["primed-token", "rotated-token"]

        OverseerrClient().provision_plex_user("t", _connection(watchlist_sync=True))

    assert seerr.post.call_args[1]["headers"]["X-XSRF-TOKEN"] == "rotated-token"


def test_the_account_still_counts_when_the_setting_does_not_take():
    """The user exists either way; reporting the whole thing failed would send
    the next person looking for an account that is already there."""
    login, _read = _provisioned()
    with _seerr() as (seerr, _):
        seerr.post.side_effect = [login, _resp(500, "boom")]
        seerr.get.return_value = _resp(200, json={"locale": "en"})

        result = OverseerrClient().provision_plex_user(
            "t", _connection(watchlist_sync=True)
        )

    assert result["status"] == "success"
    assert "watchlist" in result["message"].lower()
    assert "500" in result["message"]


def test_no_settings_write_without_a_user_id():
    """Posting to /user/None/settings/main would be a confusing 404 at best."""
    with _seerr() as (seerr, _):
        seerr.post.side_effect = [_resp(200, json={}), _resp(200)]
        seerr.get.return_value = _resp(200, json={"locale": "en"})

        result = OverseerrClient().provision_plex_user(
            "t", _connection(watchlist_sync=True)
        )

    assert result["status"] == "success"
    assert seerr.post.call_count == 1


def test_the_form_refuses_watchlist_sync_without_account_creation(app):
    """The setting is written during account creation, on the session creating
    the account returns. Without it the box stays ticked and never takes effect,
    which is the same silent nothing the flag exists to prevent."""
    from app.forms.connections import ConnectionForm

    with app.test_request_context():
        form = ConnectionForm(
            connection_type="overseerr",
            name="Seerr",
            url="https://seerr.local",
            media_server_id=1,
            provision_plex_users=False,
            enable_watchlist_sync=True,
            meta={"csrf": False},
        )
        form.media_server_id.choices = [(1, "Plex")]

        assert form.validate() is False
        assert form.enable_watchlist_sync.errors

        form.provision_plex_users.data = True

        assert form.validate() is True


def test_watchlist_failures_are_reported_not_raised():
    """Best effort throughout: this runs off an invite the user already accepted."""
    login, _read = _provisioned()
    with _seerr() as (seerr, _):
        seerr.post.side_effect = [login, OSError("connection refused")]
        seerr.get.return_value = _resp(200, json={"locale": "en"})

        result = OverseerrClient().provision_plex_user(
            "t", _connection(watchlist_sync=True)
        )

    assert result["status"] == "success"
    assert "connection refused" in result["message"]
