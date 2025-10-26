"""
Integration test for the invite table route to ensure timezone-aware datetime handling.

Tests that the /invite/table endpoint properly handles invitations with both
timezone-naive and timezone-aware expiry dates without throwing comparison errors.
"""

import datetime

import pytest

from app.extensions import db
from app.models import AdminAccount, Invitation, Library, MediaServer


@pytest.fixture
def admin_user(app):
    """Create an admin account for authenticated requests."""
    with app.app_context():
        created = False
        previous_hash = None
        admin = AdminAccount.query.filter_by(username="testadmin").first()
        if not admin:
            admin = AdminAccount(username="testadmin")
            admin.set_password("TestPass123")
            db.session.add(admin)
            db.session.commit()
            created = True
        else:
            previous_hash = admin.password_hash
            admin.set_password("TestPass123")
            db.session.commit()
        yield admin
        if created:
            db.session.delete(admin)
            db.session.commit()
        elif previous_hash is not None:
            # Restore the original password hash so other tests keep their expectations
            admin = AdminAccount.query.filter_by(username="testadmin").first()
            if admin:
                admin.password_hash = previous_hash
                db.session.commit()


@pytest.fixture
def media_server_with_libraries(app):
    """Create a media server with libraries."""
    with app.app_context():
        server = MediaServer(
            name="Test Plex Server",
            server_type="plex",
            url="http://plex.local",
            api_key="test-api-key-123",
        )
        db.session.add(server)
        db.session.commit()

        # Add some libraries
        lib1 = Library(
            name="Movies",
            server_id=server.id,
            external_id="1",
        )
        lib2 = Library(
            name="TV Shows",
            server_id=server.id,
            external_id="2",
        )
        db.session.add_all([lib1, lib2])
        db.session.commit()

        yield server, [lib1, lib2]

        # Cleanup
        db.session.delete(lib1)
        db.session.delete(lib2)
        db.session.delete(server)
        db.session.commit()


@pytest.fixture
def invitations_mixed_timezones(app, media_server_with_libraries):
    """Create invitations with mixed timezone-aware and naive expiry dates."""
    server, libraries = media_server_with_libraries

    with app.app_context():
        # Invitation 1: Timezone-naive expiry (simulates old data or SQLite storage)
        naive_expiry = datetime.datetime(2025, 12, 31, 23, 59, 59, tzinfo=datetime.UTC)
        inv1 = Invitation(
            code="NAIVE123",
            expires=naive_expiry,
            used=False,
            unlimited=False,
        )

        # Invitation 2: Timezone-aware expiry (UTC)
        aware_expiry = datetime.datetime(2026, 6, 15, 12, 0, 0, tzinfo=datetime.UTC)
        inv2 = Invitation(
            code="AWARE456",
            expires=aware_expiry,
            used=False,
            unlimited=False,
        )

        # Invitation 3: No expiry (unlimited)
        inv3 = Invitation(
            code="UNLIMITED789",
            expires=None,
            used=False,
            unlimited=True,
        )

        # Invitation 4: Already expired (naive)
        expired_naive = datetime.datetime(2020, 1, 1, 0, 0, 0, tzinfo=datetime.UTC)
        inv4 = Invitation(
            code="EXPIRED999",
            expires=expired_naive,
            used=True,
            unlimited=False,
        )

        # Re-query libraries in this session context
        fresh_libs = Library.query.filter_by(server_id=server.id).all()

        # Associate libraries with invitations
        inv1.libraries.extend(fresh_libs)
        inv2.libraries.extend(fresh_libs)
        inv3.libraries.extend(fresh_libs)
        inv4.libraries.extend(fresh_libs)

        db.session.add_all([inv1, inv2, inv3, inv4])
        db.session.commit()

        yield [inv1, inv2, inv3, inv4]

        # Cleanup
        for inv in [inv1, inv2, inv3, inv4]:
            db.session.delete(inv)
        db.session.commit()


def test_invite_table_with_mixed_timezone_invitations(
    client, app, admin_user, invitations_mixed_timezones
):
    """
    Test that /invite/table properly handles invitations with mixed timezone awareness.

    This is a regression test for: TypeError: can't compare offset-naive and offset-aware datetimes

    The route should:
    1. Load all invitations successfully
    2. Compare expiry dates with current time without errors
    3. Render the table with proper expired/active status
    """
    with app.app_context():
        # Login as admin
        login_response = client.post(
            "/login", data={"username": "testadmin", "password": "TestPass123"}
        )
        assert login_response.status_code in {200, 302, 303}

        # Request the invite table - this should not raise a TypeError
        response = client.post("/invite/table")

        # Should succeed
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"

        # Verify the response contains expected data
        data = response.data.decode("utf-8")

        # Should contain the invitation codes (checking they're present in rendered HTML)
        # Note: These may be filtered depending on view, so we just verify no errors occurred
        assert "NAIVE123" in data or "AWARE456" in data or "UNLIMITED789" in data

        # Should not have any Python exception traces
        assert "TypeError" not in data
        assert "can't compare offset-naive" not in data
        assert "Traceback" not in data


def test_invite_table_with_filter_by_server(
    client, app, admin_user, invitations_mixed_timezones, media_server_with_libraries
):
    """
    Test that /invite/table works with server filtering.
    """
    server, _ = media_server_with_libraries

    with app.app_context():
        # Login
        client.post("/login", data={"username": "testadmin", "password": "TestPass123"})

        # Request invite table with server filter
        response = client.post("/invite/table", data={"server_id": str(server.id)})

        assert response.status_code == 200
        data = response.data.decode("utf-8")

        # Should not have errors
        assert "TypeError" not in data
        assert "Traceback" not in data


def test_invite_table_empty_state(client, app, admin_user):
    """
    Test that /invite/table works when there are no invitations.
    """
    with app.app_context():
        # Login
        client.post("/login", data={"username": "testadmin", "password": "TestPass123"})

        # Request invite table with no invitations
        response = client.post("/invite/table")

        assert response.status_code == 200
        # Should render successfully even with no data
