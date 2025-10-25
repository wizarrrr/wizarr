"""
Test for the datetime timezone fix in expiry service.

This test specifically validates that get_expiring_this_week_users() 
correctly handles naive datetime values from the database.
"""
import datetime
from datetime import UTC, timedelta

import pytest

from app.extensions import db
from app.models import MediaServer, User
from app.services.expiry import get_expiring_this_week_users


def test_get_expiring_this_week_users_with_naive_datetime(app, session):
    """Test that get_expiring_this_week_users handles naive datetime from DB correctly."""
    with app.app_context():
        # Create a test server
        server = MediaServer(
            name="Test Server",
            server_type="jellyfin",
            url="http://localhost:8096",
            api_key="test-key",
        )
        session.add(server)
        session.flush()
        
        # Create a user with an expiry date 3 days from now
        # Simulating a naive datetime as stored in SQLite database
        expires_in_3_days = datetime.datetime.now(UTC) + timedelta(days=3)
        # Remove timezone info to simulate what SQLite returns
        expires_naive = expires_in_3_days.replace(tzinfo=None)
        
        user = User(
            token="test-token-123",
            username="test_expiring_user",
            email="test@example.com",
            code="TEST123",
            expires=expires_naive,
            server_id=server.id,
        )
        session.add(user)
        session.commit()
        
        # This should not raise "TypeError: can't subtract offset-naive and offset-aware datetimes"
        result = get_expiring_this_week_users()
        
        # Verify the user is in the results
        assert len(result) == 1
        assert result[0]["user"].username == "test_expiring_user"
        assert result[0]["days_left"] == 3
        assert result[0]["urgency"] == "urgent"


def test_get_expiring_this_week_users_with_aware_datetime(app, session):
    """Test that get_expiring_this_week_users also handles timezone-aware datetime."""
    with app.app_context():
        # Create a test server
        server = MediaServer(
            name="Test Server",
            server_type="jellyfin",
            url="http://localhost:8096",
            api_key="test-key",
        )
        session.add(server)
        session.flush()
        
        # Create a user with a timezone-aware expiry date 5 days from now
        expires_in_5_days = datetime.datetime.now(UTC) + timedelta(days=5)
        
        user = User(
            token="test-token-456",
            username="test_expiring_user_aware",
            email="test2@example.com",
            code="TEST456",
            expires=expires_in_5_days,
            server_id=server.id,
        )
        session.add(user)
        session.commit()
        
        # This should work with timezone-aware datetime too
        result = get_expiring_this_week_users()
        
        # Verify the user is in the results
        assert len(result) == 1
        assert result[0]["user"].username == "test_expiring_user_aware"
        assert result[0]["days_left"] == 5
        assert result[0]["urgency"] == "soon"


def test_get_expiring_this_week_users_excludes_already_expired(app, session):
    """Test that users who already expired are excluded."""
    with app.app_context():
        # Create a test server
        server = MediaServer(
            name="Test Server",
            server_type="jellyfin",
            url="http://localhost:8096",
            api_key="test-key",
        )
        session.add(server)
        session.flush()
        
        # Create a user that expired 1 day ago
        expired_yesterday = datetime.datetime.now(UTC) - timedelta(days=1)
        expired_naive = expired_yesterday.replace(tzinfo=None)
        
        user = User(
            token="test-token-expired",
            username="test_expired_user",
            email="expired@example.com",
            code="EXPIRED123",
            expires=expired_naive,
            server_id=server.id,
        )
        session.add(user)
        session.commit()
        
        # Should return empty list as the user is already expired
        result = get_expiring_this_week_users()
        
        assert len(result) == 0


def test_get_expiring_this_week_users_excludes_far_future(app, session):
    """Test that users expiring beyond 7 days are excluded."""
    with app.app_context():
        # Create a test server
        server = MediaServer(
            name="Test Server",
            server_type="jellyfin",
            url="http://localhost:8096",
            api_key="test-key",
        )
        session.add(server)
        session.flush()
        
        # Create a user that expires in 10 days
        expires_in_10_days = datetime.datetime.now(UTC) + timedelta(days=10)
        expires_naive = expires_in_10_days.replace(tzinfo=None)
        
        user = User(
            token="test-token-future",
            username="test_future_user",
            email="future@example.com",
            code="FUTURE123",
            expires=expires_naive,
            server_id=server.id,
        )
        session.add(user)
        session.commit()
        
        # Should return empty list as the user expires too far in the future
        result = get_expiring_this_week_users()
        
        assert len(result) == 0
