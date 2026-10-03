"""
Regression tests: the "Recently Expired" panel is bounded by a time window.

The panel is labelled "Recently Expired Users" but `get_expired_users()`
returned the full history, so a install with old expirations showed months-old
rows above the live user table. These cover the window filter, the selectable
30/60/90/all choices and their persistence, and the companion
"All Expired Users" section staying deliberately unbounded.
"""

import datetime

import pytest

from app.extensions import db
from app.models import AdminAccount, ExpiredUser, MediaServer, Settings
from app.services.expiry import (
    EXPIRED_WINDOW_DEFAULT,
    EXPIRED_WINDOW_SETTING,
    get_expired_users,
    get_expired_users_window,
    has_any_expired_users,
    parse_expired_users_window,
    set_expired_users_window,
)


@pytest.fixture
def admin_user(app):
    """Create an admin account for authenticated requests."""
    with app.app_context():
        admin = AdminAccount.query.filter_by(username="testadmin").first()
        created = False
        if not admin:
            admin = AdminAccount(username="testadmin")
            admin.set_password("TestPass123")
            db.session.add(admin)
            db.session.commit()
            created = True
        else:
            admin.set_password("TestPass123")
            db.session.commit()
        yield admin
        if created:
            db.session.delete(admin)
            db.session.commit()


def _login(client):
    client.post("/login", data={"username": "testadmin", "password": "TestPass123"})


def _server() -> MediaServer:
    server = MediaServer(
        name="Plex",
        server_type="plex",
        url="http://plex.example.com",
        api_key="test-key",
    )
    db.session.add(server)
    db.session.commit()
    return server


def _expired_row(*, username: str, days_ago: float, server_id: int) -> ExpiredUser:
    """Insert an ExpiredUser whose deleted_at is `days_ago` in the past.

    `deleted_at` is written naive, exactly as the column stores it in
    production (db.DateTime with a datetime.now(UTC) default).
    """
    now_naive = datetime.datetime.now(datetime.UTC).replace(tzinfo=None)
    deleted_at = now_naive - datetime.timedelta(days=days_ago)
    row = ExpiredUser(
        original_user_id=abs(hash(username)) % 100_000,
        username=username,
        email=f"{username}@example.com",
        server_id=server_id,
        expired_at=deleted_at,
        deleted_at=deleted_at,
    )
    db.session.add(row)
    db.session.commit()
    return row


# --- parse_expired_users_window ---------------------------------------------


@pytest.mark.parametrize("raw", [30, 60, 90, "30", "60", "90", " 60 "])
def test_parse_window_accepts_allowed_choices(app, raw):
    with app.app_context():
        assert parse_expired_users_window(raw) == int(str(raw).strip())


@pytest.mark.parametrize("raw", ["all", "ALL", "none", " All "])
def test_parse_window_accepts_all_time(app, raw):
    with app.app_context():
        assert parse_expired_users_window(raw) is None


@pytest.mark.parametrize("raw", ["", "  ", "banana", "45", "9999", "-1", None])
def test_parse_window_falls_back_to_default(app, raw):
    """An unknown or crafted value must not raise, and must not widen the view."""
    with app.app_context():
        assert parse_expired_users_window(raw) == EXPIRED_WINDOW_DEFAULT


# --- get_expired_users ------------------------------------------------------


def test_window_excludes_rows_older_than_the_window(app, session):
    with app.app_context():
        server = _server()
        _expired_row(username="stale", days_ago=200, server_id=server.id)

        assert get_expired_users(within_days=30) == []


def test_window_includes_rows_inside_the_window(app, session):
    with app.app_context():
        server = _server()
        _expired_row(username="fresh", days_ago=3, server_id=server.id)

        names = [u.username for u in get_expired_users(within_days=30)]
        assert names == ["fresh"]


def test_window_boundaries_are_respected(app, session):
    with app.app_context():
        server = _server()
        _expired_row(username="inside_30", days_ago=29, server_id=server.id)
        _expired_row(username="inside_60", days_ago=45, server_id=server.id)
        _expired_row(username="inside_90", days_ago=75, server_id=server.id)
        _expired_row(username="outside_all", days_ago=200, server_id=server.id)

        assert {u.username for u in get_expired_users(within_days=30)} == {"inside_30"}
        assert {u.username for u in get_expired_users(within_days=60)} == {
            "inside_30",
            "inside_60",
        }
        assert {u.username for u in get_expired_users(within_days=90)} == {
            "inside_30",
            "inside_60",
            "inside_90",
        }


def test_none_returns_the_full_history(app, session):
    with app.app_context():
        server = _server()
        _expired_row(username="ancient", days_ago=900, server_id=server.id)
        _expired_row(username="recent", days_ago=1, server_id=server.id)

        assert {u.username for u in get_expired_users(within_days=None)} == {
            "ancient",
            "recent",
        }


def test_results_stay_ordered_most_recent_first(app, session):
    with app.app_context():
        server = _server()
        _expired_row(username="older", days_ago=20, server_id=server.id)
        _expired_row(username="newer", days_ago=2, server_id=server.id)

        assert [u.username for u in get_expired_users(within_days=30)] == [
            "newer",
            "older",
        ]


def test_default_argument_is_bounded(app, session):
    """Calling with no argument must not return the full history."""
    with app.app_context():
        server = _server()
        _expired_row(username="stale", days_ago=200, server_id=server.id)

        assert get_expired_users() == []


# --- setting persistence ----------------------------------------------------


def test_window_setting_round_trip(app, session):
    with app.app_context():
        assert get_expired_users_window() == EXPIRED_WINDOW_DEFAULT

        set_expired_users_window(90)
        assert get_expired_users_window() == 90

        set_expired_users_window(None)
        assert get_expired_users_window() is None

        set_expired_users_window(60)
        assert get_expired_users_window() == 60


def test_corrupt_stored_setting_falls_back_to_default(app, session):
    with app.app_context():
        db.session.add(Settings(key=EXPIRED_WINDOW_SETTING, value="not-a-window"))
        db.session.commit()

        assert get_expired_users_window() == EXPIRED_WINDOW_DEFAULT


def test_has_any_expired_users(app, session):
    with app.app_context():
        assert has_any_expired_users() is False

        server = _server()
        _expired_row(username="stale", days_ago=200, server_id=server.id)

        assert has_any_expired_users() is True


# --- routes -----------------------------------------------------------------


def test_recently_expired_route_defaults_to_the_stored_window(
    app, session, client, admin_user
):
    with app.app_context():
        server = _server()
        _expired_row(username="staleuser", days_ago=200, server_id=server.id)
        _expired_row(username="freshuser", days_ago=2, server_id=server.id)

    _login(client)
    body = client.get("/recently-expired/table").get_data(as_text=True)

    assert "freshuser" in body
    assert "staleuser" not in body


def test_recently_expired_route_persists_an_explicit_window(
    app, session, client, admin_user
):
    with app.app_context():
        server = _server()
        _expired_row(username="staleuser", days_ago=200, server_id=server.id)

    _login(client)
    body = client.get("/recently-expired/table?days=all").get_data(as_text=True)
    assert "staleuser" in body

    with app.app_context():
        assert get_expired_users_window() is None

    # the stored choice now applies without the query string
    body = client.get("/recently-expired/table").get_data(as_text=True)
    assert "staleuser" in body


def test_all_expired_users_route_stays_unbounded(app, session, client, admin_user):
    """The "All Expired Users" section must keep showing the full history."""
    with app.app_context():
        server = _server()
        _expired_row(username="staleuser", days_ago=400, server_id=server.id)

    _login(client)
    body = client.get("/expired-users/table").get_data(as_text=True)

    assert "staleuser" in body


def test_selector_marks_the_active_window(app, session, client, admin_user):
    with app.app_context():
        server = _server()
        _expired_row(username="freshuser", days_ago=2, server_id=server.id)

    _login(client)
    body = client.get("/recently-expired/table?days=60").get_data(as_text=True)

    assert 'id="expired_window_sel"' in body
    assert '<option value="60" selected>' in body
    assert 'value="all"' in body


def test_empty_window_keeps_the_selector_reachable(app, session, client, admin_user):
    """A window that filters every row must not hide the control to widen it."""
    with app.app_context():
        server = _server()
        _expired_row(username="staleuser", days_ago=300, server_id=server.id)

    _login(client)
    body = client.get("/recently-expired/table?days=30").get_data(as_text=True)

    assert "staleuser" not in body
    assert 'id="expired_window_sel"' in body
    assert "No users expired in the last" in body
