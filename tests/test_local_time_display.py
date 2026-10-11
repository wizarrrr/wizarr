"""
Timestamps are stored as UTC and must be shown, and edited, in local time.

Covers the shared conversion helpers, both date filters, and the user edit
modal's expiry field, which has to round-trip: the value it renders in local
time must be stored back as the same UTC instant.
"""

import datetime
from zoneinfo import ZoneInfo

import pytest

from app import jinja_filters
from app.extensions import db
from app.models import AdminAccount, MediaServer, User

EDMONTON = ZoneInfo("America/Edmonton")


def _naive(*args):
    """A naive wall-clock datetime, the way SQLite hands stored values back."""
    return datetime.datetime(*args, tzinfo=datetime.UTC).replace(tzinfo=None)


@pytest.fixture
def edmonton(monkeypatch):
    monkeypatch.setattr(jinja_filters, "_LOCAL_TIMEZONE", EDMONTON)


@pytest.fixture
def admin_user(app):
    with app.app_context():
        admin = AdminAccount.query.filter_by(username="tzadmin").first()
        if not admin:
            admin = AdminAccount(username="tzadmin")
            db.session.add(admin)
        admin.set_password("TestPass123")
        db.session.commit()
        yield admin
        db.session.delete(admin)
        db.session.commit()


def _login(client):
    client.post("/login", data={"username": "tzadmin", "password": "TestPass123"})


def test_to_local_treats_naive_as_utc(edmonton):
    # January 2025: Edmonton was MST, UTC-7 (past dates, so tzdata rule changes cannot move them)
    local = jinja_filters.to_local(_naive(2025, 1, 15, 7, 0))
    assert (local.hour, local.utcoffset()) == (0, datetime.timedelta(hours=-7))


def test_to_local_leaves_non_datetimes_alone(edmonton):
    day = datetime.date(2025, 1, 15)
    assert jinja_filters.to_local(day) is day
    assert jinja_filters.to_local("soon") == "soon"


def test_local_to_utc_round_trips(edmonton):
    stored = datetime.datetime(2025, 7, 1, 5, 30, tzinfo=datetime.UTC)
    shown = jinja_filters.to_local(stored).replace(tzinfo=None)
    assert shown == _naive(2025, 6, 30, 23, 30)  # MDT, UTC-6
    assert jinja_filters.local_to_utc(shown) == stored


def test_local_to_utc_keeps_explicit_offset(edmonton):
    aware = datetime.datetime(2025, 1, 1, tzinfo=datetime.UTC)
    assert jinja_filters.local_to_utc(aware) == aware


def test_human_date_renders_local_time(edmonton):
    assert (
        jinja_filters.human_date(_naive(2025, 1, 15, 7, 0))
        == "Jan 15, 2025 at 12:00 AM"
    )


def test_local_date_renders_local_time(edmonton):
    assert (
        jinja_filters.local_date(_naive(2025, 1, 15, 7, 0), "%Y-%m-%d %H:%M")
        == "2025-01-15 00:00"
    )


def test_user_modal_expiry_round_trips_in_local_time(
    client, app, session, admin_user, edmonton
):
    with app.app_context():
        server = MediaServer(
            name="TZ Server", server_type="jellyfin", url="http://tz", api_key="k"
        )
        db.session.add(server)
        db.session.commit()
        user = User(
            token="t-tz",
            username="user_tz",
            email="tz@example.com",
            code="TZCODE",
            expires=_naive(2025, 1, 15, 7, 0),  # 00:00 MST
            server_id=server.id,
        )
        db.session.add(user)
        db.session.commit()
        user_id = user.id

    _login(client)

    modal = client.get(f"/user/{user_id}").data.decode("utf-8")
    assert 'value="2025-01-15T00:00"' in modal

    # The admin types midnight local on Mar 1 (MST); that is 07:00 UTC.
    client.post(f"/user/{user_id}", data={"expires": "2025-03-01T00:00"})

    with app.app_context():
        saved_user = db.session.get(User, user_id)
        assert saved_user is not None
        saved = saved_user.expires
        assert saved.replace(tzinfo=None) == _naive(2025, 3, 1, 7, 0)


def test_resolver_prefers_localtime_link_over_tzname(monkeypatch):
    """Without TZ, an abbreviation like "MST" must not win over the host zone."""
    monkeypatch.delenv("TZ", raising=False)
    monkeypatch.setattr(jinja_filters.time, "tzname", ("MST", "MDT"))
    monkeypatch.setattr(jinja_filters.time, "daylight", 1)
    monkeypatch.setattr(jinja_filters, "_zone_from_localtime_link", lambda: EDMONTON)

    assert jinja_filters._resolve_local_timezone() is EDMONTON


def test_resolver_does_not_use_tzname_abbreviation_when_dst_applies(monkeypatch):
    monkeypatch.delenv("TZ", raising=False)
    monkeypatch.setattr(jinja_filters.time, "tzname", ("MST", "MDT"))
    monkeypatch.setattr(jinja_filters.time, "daylight", 1)
    monkeypatch.setattr(jinja_filters, "_zone_from_localtime_link", lambda: None)

    assert jinja_filters._resolve_local_timezone() != ZoneInfo("MST")


def test_zone_from_localtime_link_reads_the_symlink(monkeypatch):
    monkeypatch.setattr(
        jinja_filters.os.path,
        "realpath",
        lambda _p: "/usr/share/zoneinfo/America/Edmonton",
    )
    assert jinja_filters._zone_from_localtime_link() == EDMONTON


def test_zone_from_localtime_link_ignores_non_zoneinfo_target(monkeypatch):
    monkeypatch.setattr(jinja_filters.os.path, "realpath", lambda _p: "/etc/localtime")
    assert jinja_filters._zone_from_localtime_link() is None
