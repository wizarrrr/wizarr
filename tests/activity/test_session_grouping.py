"""
Comprehensive tests for session grouping logic.

Tests the multi-level matching strategy that handles real-world scenarios where
Plex creates new sessionKeys for subtitle changes, audio changes, app restarts, etc.
"""

from datetime import UTC, datetime, timedelta

import pytest

from app.activity.domain.models import ActivityEvent
from app.models import ActivitySession, MediaServer
from app.services.activity.ingestion import ActivityIngestionService


@pytest.fixture
def media_server(session):
    """Create a test media server."""
    server = MediaServer(
        name="Test Plex Server",
        server_type="plex",
        url="http://localhost:32400",
        api_key="test-api-key",
        verified=True,
    )
    session.add(server)
    session.commit()
    return server


@pytest.fixture
def ingestion_service():
    """Create activity ingestion service instance."""
    return ActivityIngestionService()


class TestSessionGroupingExactMediaId:
    """Test exact media_id matching (highest confidence)."""

    def test_groups_with_exact_media_id_match(
        self, session, media_server, ingestion_service
    ):
        """Sessions with same media_id should be grouped."""
        # Create first session
        session1 = ActivitySession(
            server_id=media_server.id,
            session_id="session-1",
            user_name="test-user",
            media_title="Test Movie",
            media_id="12345",
            device_name="Apple TV",
            started_at=datetime.now(UTC),
            active=False,
        )
        session.add(session1)
        session.flush()
        session1.reference_id = session1.id
        session.commit()

        # Create second session 5 minutes later
        event2 = ActivityEvent(
            event_type="session_start",
            server_id=media_server.id,
            session_id="session-2",
            user_name="test-user",
            media_title="Test Movie",
            media_id="12345",
            device_name="Apple TV",
            timestamp=datetime.now(UTC) + timedelta(minutes=5),
        )

        session2 = ActivitySession(
            server_id=event2.server_id,
            session_id=event2.session_id,
            user_name=event2.user_name,
            media_title=event2.media_title,
            media_id=event2.media_id,
            device_name=event2.device_name,
            started_at=event2.timestamp,
            active=True,
        )
        session.add(session2)
        session.flush()

        # Apply grouping
        ingestion_service._apply_session_grouping(session2, event2)
        session.commit()

        # Should be grouped with session1
        assert session2.reference_id == session1.id
        assert session2.reference_id == session1.reference_id

    def test_does_not_group_different_media_id(
        self, session, media_server, ingestion_service
    ):
        """Sessions with different media_id should NOT be grouped."""
        # Create first session
        session1 = ActivitySession(
            server_id=media_server.id,
            session_id="session-1",
            user_name="test-user",
            media_title="Test Movie",
            media_id="12345",
            device_name="Apple TV",
            started_at=datetime.now(UTC),
            active=False,
        )
        session.add(session1)
        session.flush()
        session1.reference_id = session1.id
        session.commit()

        # Create second session with different media_id
        event2 = ActivityEvent(
            event_type="session_start",
            server_id=media_server.id,
            session_id="session-2",
            user_name="test-user",
            media_title="Different Movie",
            media_id="67890",
            device_name="Apple TV",
            timestamp=datetime.now(UTC) + timedelta(minutes=5),
        )

        session2 = ActivitySession(
            server_id=event2.server_id,
            session_id=event2.session_id,
            user_name=event2.user_name,
            media_title=event2.media_title,
            media_id=event2.media_id,
            device_name=event2.device_name,
            started_at=event2.timestamp,
            active=True,
        )
        session.add(session2)
        session.flush()

        # Apply grouping
        ingestion_service._apply_session_grouping(session2, event2)
        session.commit()

        # Should NOT be grouped
        assert session2.reference_id == session2.id
        assert session2.reference_id != session1.reference_id


class TestSessionGroupingTitleDeviceFallback:
    """Test title+device fallback matching (handles missing media_id)."""

    def test_groups_by_title_and_device_when_media_id_missing(
        self, session, media_server, ingestion_service
    ):
        """
        When media_id is missing/unknown, should fall back to title+device matching.

        This handles the real-world scenario where:
        1. User starts watching (media_id not yet enriched -> "Unknown")
        2. User changes subtitle track (Plex creates new sessionKey)
        3. New session also has media_id="Unknown" initially
        4. Should still group them together via title+device
        """
        # Create first session with unknown media_id
        session1 = ActivitySession(
            server_id=media_server.id,
            session_id="session-1",
            user_name="test-user",
            media_title="Fauda - Season 4 - Episode 6",
            media_id=None,  # Not yet enriched
            device_name="Apple TV",
            started_at=datetime.now(UTC),
            active=False,
        )
        session.add(session1)
        session.flush()
        session1.reference_id = session1.id
        session.commit()

        # Create second session (subtitle change) - also no media_id yet
        event2 = ActivityEvent(
            event_type="session_start",
            server_id=media_server.id,
            session_id="session-2",
            user_name="test-user",
            media_title="Fauda - Season 4 - Episode 6",
            media_id=None,  # Also not enriched yet
            device_name="Apple TV",
            timestamp=datetime.now(UTC) + timedelta(seconds=30),
        )

        session2 = ActivitySession(
            server_id=event2.server_id,
            session_id=event2.session_id,
            user_name=event2.user_name,
            media_title=event2.media_title,
            media_id=event2.media_id,
            device_name=event2.device_name,
            started_at=event2.timestamp,
            active=True,
        )
        session.add(session2)
        session.flush()

        # Apply grouping - should match via title+device
        ingestion_service._apply_session_grouping(session2, event2)
        session.commit()

        # Should be grouped via title+device fallback
        assert session2.reference_id == session1.id

    def test_groups_mixed_enrichment_states(
        self, session, media_server, ingestion_service
    ):
        """
        Should group sessions even when one is enriched and other is not.

        Real-world scenario:
        1. Session 1 starts and gets enriched with media_id
        2. User changes audio track
        3. Session 2 starts but not yet enriched (media_id is None)
        4. Should still group them via title+device fallback
        """
        # Create first session - already enriched
        session1 = ActivitySession(
            server_id=media_server.id,
            session_id="session-1",
            user_name="test-user",
            media_title="Fauda - Season 4 - Episode 6",
            media_id="144863",  # Enriched
            device_name="Apple TV",
            started_at=datetime.now(UTC),
            active=False,
        )
        session.add(session1)
        session.flush()
        session1.reference_id = session1.id
        session.commit()

        # Create second session - not yet enriched
        event2 = ActivityEvent(
            event_type="session_start",
            server_id=media_server.id,
            session_id="session-2",
            user_name="test-user",
            media_title="Fauda - Season 4 - Episode 6",
            media_id=None,  # Not enriched yet
            device_name="Apple TV",
            timestamp=datetime.now(UTC) + timedelta(minutes=1),
        )

        session2 = ActivitySession(
            server_id=event2.server_id,
            session_id=event2.session_id,
            user_name=event2.user_name,
            media_title=event2.media_title,
            media_id=event2.media_id,
            device_name=event2.device_name,
            started_at=event2.timestamp,
            active=True,
        )
        session.add(session2)
        session.flush()

        # Apply grouping
        ingestion_service._apply_session_grouping(session2, event2)
        session.commit()

        # Should be grouped via title+device fallback
        assert session2.reference_id == session1.id


class TestSessionGroupingTimeWindow:
    """Test extended 2-hour time window."""

    def test_groups_within_2_hour_window(
        self, session, media_server, ingestion_service
    ):
        """Sessions within 2 hours should be grouped."""
        # Create first session
        session1 = ActivitySession(
            server_id=media_server.id,
            session_id="session-1",
            user_name="test-user",
            media_title="Test Movie",
            media_id="12345",
            device_name="Apple TV",
            started_at=datetime.now(UTC),
            active=False,
        )
        session.add(session1)
        session.flush()
        session1.reference_id = session1.id
        session.commit()

        # Create second session 1.5 hours later (within 2-hour window)
        event2 = ActivityEvent(
            event_type="session_start",
            server_id=media_server.id,
            session_id="session-2",
            user_name="test-user",
            media_title="Test Movie",
            media_id="12345",
            device_name="Apple TV",
            timestamp=datetime.now(UTC) + timedelta(hours=1.5),
        )

        session2 = ActivitySession(
            server_id=event2.server_id,
            session_id=event2.session_id,
            user_name=event2.user_name,
            media_title=event2.media_title,
            media_id=event2.media_id,
            device_name=event2.device_name,
            started_at=event2.timestamp,
            active=True,
        )
        session.add(session2)
        session.flush()

        # Apply grouping
        ingestion_service._apply_session_grouping(session2, event2)
        session.commit()

        # Should be grouped (within 2-hour window)
        assert session2.reference_id == session1.id

    def test_does_not_group_beyond_2_hour_window(
        self, session, media_server, ingestion_service
    ):
        """Sessions beyond 2 hours should NOT be grouped."""
        # Create first session
        session1 = ActivitySession(
            server_id=media_server.id,
            session_id="session-1",
            user_name="test-user",
            media_title="Test Movie",
            media_id="12345",
            device_name="Apple TV",
            started_at=datetime.now(UTC),
            active=False,
        )
        session.add(session1)
        session.flush()
        session1.reference_id = session1.id
        session.commit()

        # Create second session 3 hours later (beyond 2-hour window)
        event2 = ActivityEvent(
            event_type="session_start",
            server_id=media_server.id,
            session_id="session-2",
            user_name="test-user",
            media_title="Test Movie",
            media_id="12345",
            device_name="Apple TV",
            timestamp=datetime.now(UTC) + timedelta(hours=3),
        )

        session2 = ActivitySession(
            server_id=event2.server_id,
            session_id=event2.session_id,
            user_name=event2.user_name,
            media_title=event2.media_title,
            media_id=event2.media_id,
            device_name=event2.device_name,
            started_at=event2.timestamp,
            active=True,
        )
        session.add(session2)
        session.flush()

        # Apply grouping
        ingestion_service._apply_session_grouping(session2, event2)
        session.commit()

        # Should NOT be grouped (beyond 2-hour window)
        assert session2.reference_id == session2.id
        assert session2.reference_id != session1.reference_id


class TestSessionGroupingRealWorldScenario:
    """Test complete real-world scenario from the bug report."""

    def test_subtitle_change_scenario(self, session, media_server, ingestion_service):
        """
        Simulate the exact scenario from the bug report:

        User watches Fauda S4E6 on Apple TV:
        1. Starts watching (14m)
        2. Changes subtitle track -> new sessionKey (3m)
        3. Changes audio language -> new sessionKey (5m)
        4. Finishes watching (40m)

        All 4 sessions should be grouped as one viewing session.
        """
        base_time = datetime.now(UTC)

        # Session 1: Initial watch (14 minutes)
        session1 = ActivitySession(
            server_id=media_server.id,
            session_id="219",
            user_name="Mtthieu",
            media_title="Fauda - Season 4 - Episode 6",
            media_id=None,  # Not enriched yet
            device_name="Apple TV",
            started_at=base_time,
            active=False,
        )
        session.add(session1)
        session.flush()
        session1.reference_id = session1.id
        session.commit()

        # Session 2: After subtitle change (3 minutes)
        event2 = ActivityEvent(
            event_type="session_start",
            server_id=media_server.id,
            session_id="220",
            user_name="Mtthieu",
            media_title="Fauda - Season 4 - Episode 6",
            media_id=None,
            device_name="Apple TV",
            timestamp=base_time + timedelta(minutes=14, seconds=30),
        )
        session2 = ActivitySession(
            server_id=event2.server_id,
            session_id=event2.session_id,
            user_name=event2.user_name,
            media_title=event2.media_title,
            media_id=event2.media_id,
            device_name=event2.device_name,
            started_at=event2.timestamp,
            active=False,
        )
        session.add(session2)
        session.flush()
        ingestion_service._apply_session_grouping(session2, event2)
        session.commit()

        # Session 3: After audio change (5 minutes)
        event3 = ActivityEvent(
            event_type="session_start",
            server_id=media_server.id,
            session_id="221",
            user_name="Mtthieu",
            media_title="Fauda - Season 4 - Episode 6",
            media_id=None,
            device_name="Apple TV",
            timestamp=base_time + timedelta(minutes=17, seconds=45),
        )
        session3 = ActivitySession(
            server_id=event3.server_id,
            session_id=event3.session_id,
            user_name=event3.user_name,
            media_title=event3.media_title,
            media_id=event3.media_id,
            device_name=event3.device_name,
            started_at=event3.timestamp,
            active=False,
        )
        session.add(session3)
        session.flush()
        ingestion_service._apply_session_grouping(session3, event3)
        session.commit()

        # Session 4: Finish watching (40 minutes)
        event4 = ActivityEvent(
            event_type="session_start",
            server_id=media_server.id,
            session_id="222",
            user_name="Mtthieu",
            media_title="Fauda - Season 4 - Episode 6",
            media_id=None,
            device_name="Apple TV",
            timestamp=base_time + timedelta(minutes=22, seconds=50),
        )
        session4 = ActivitySession(
            server_id=event4.server_id,
            session_id=event4.session_id,
            user_name=event4.user_name,
            media_title=event4.media_title,
            media_id=event4.media_id,
            device_name=event4.device_name,
            started_at=event4.timestamp,
            active=True,
        )
        session.add(session4)
        session.flush()
        ingestion_service._apply_session_grouping(session4, event4)
        session.commit()

        # All sessions should share the same reference_id
        assert session2.reference_id == session1.id
        assert session3.reference_id == session1.id
        assert session4.reference_id == session1.id

        # UI should display as single grouped session
        assert (
            session1.reference_id
            == session2.reference_id
            == session3.reference_id
            == session4.reference_id
        )
