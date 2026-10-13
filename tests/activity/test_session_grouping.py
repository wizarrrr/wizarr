"""
Session grouping.

Plex makes a new session key when the user changes the subtitle track or the
audio track, or restarts the app. The ingestion puts these sessions in one
group: same media id first, then same title and device, inside a 2-hour window.
"""

from datetime import UTC, datetime, timedelta

import pytest

from app.activity.domain.models import ActivityEvent
from app.models import ActivitySession

TITLE = "Fauda - Season 4 - Episode 6"


def start(session, service, server_id, session_id, started_at, media_id, title=TITLE):
    """Store a new session row and group it as a session start does."""
    values = {
        "server_id": server_id,
        "session_id": session_id,
        "user_name": "test-user",
        "media_title": title,
        "media_id": media_id,
        "device_name": "Apple TV",
    }
    row = ActivitySession(started_at=started_at, active=True, **values)
    session.add(row)
    session.flush()
    service._apply_session_grouping(
        row,
        ActivityEvent(event_type="session_start", timestamp=started_at, **values),
    )
    session.commit()
    return row


@pytest.mark.parametrize(
    ("first_media_id", "media_id", "title", "gap", "grouped"),
    [
        pytest.param(
            "12345", "12345", TITLE, timedelta(minutes=5), True, id="same-media-id"
        ),
        pytest.param(
            "12345",
            "67890",
            "Different Movie",
            timedelta(minutes=5),
            False,
            id="different-media-id",
        ),
        # The media id is not known yet: title and device match.
        pytest.param(None, None, TITLE, timedelta(seconds=30), True, id="no-media-id"),
        pytest.param(
            "144863", None, TITLE, timedelta(minutes=1), True, id="one-media-id"
        ),
        pytest.param(
            "12345", "12345", TITLE, timedelta(hours=1.5), True, id="inside-window"
        ),
        pytest.param(
            "12345", "12345", TITLE, timedelta(hours=3), False, id="outside-window"
        ),
    ],
)
def test_session_grouping(
    session, server, service, first_media_id, media_id, title, gap, grouped
):
    now = datetime.now(UTC)
    first = start(session, service, server.id, "session-1", now, first_media_id)
    second = start(session, service, server.id, "session-2", now + gap, media_id, title)

    assert first.reference_id == first.id
    assert second.reference_id == (first.id if grouped else second.id)


def test_subtitle_and_audio_changes_make_one_group(session, server, service):
    """The scenario of the bug report: four session keys for one viewing."""
    base = datetime.now(UTC)
    offsets = [
        timedelta(0),
        timedelta(minutes=14, seconds=30),
        timedelta(minutes=17, seconds=45),
        timedelta(minutes=22, seconds=50),
    ]
    rows = [
        start(session, service, server.id, str(219 + i), base + offset, None)
        for i, offset in enumerate(offsets)
    ]

    assert [row.reference_id for row in rows] == [rows[0].id] * 4
