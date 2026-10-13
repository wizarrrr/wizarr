"""
Collector behavior: client reuse, failed polls, outages, app context, batching
and collector threads.
"""

import threading
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from flask import has_app_context

from app.activity.monitoring import monitor as monitor_module
from app.activity.monitoring.collectors.audiobookshelf import AudiobookshelfCollector
from app.activity.monitoring.collectors.emby import EmbyCollector
from app.activity.monitoring.collectors.jellyfin import JellyfinCollector
from app.activity.monitoring.collectors.polling import PollingCollector
from app.activity.monitoring.monitor import POLL_OUTAGE_LIMIT, WebSocketMonitor
from app.extensions import db
from app.models import MediaServer

FACTORY = "app.services.media.service.get_client_for_media_server"


def make_server(**values):
    defaults = {
        "id": 1,
        "name": "Server",
        "server_type": "jellyfin",
        "url": "http://a",
        "api_key": "k1",
    }
    defaults.update(values)
    return SimpleNamespace(**defaults)


def session_payload(session_id, state="playing", position_ms=1000):
    return {
        "session_id": session_id,
        "user_name": "alice",
        "media_title": "Movie",
        "state": state,
        "position_ms": position_ms,
        "duration_ms": 10_000,
    }


class FakeClient:
    def __init__(self, results):
        self.results = list(results)
        self.calls = 0
        self.app_context_seen = []

    def now_playing(self):
        self.calls += 1
        self.app_context_seen.append(has_app_context())
        result = self.results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


@pytest.fixture
def built_clients(monkeypatch):
    """Patch the client factory and record each client that it builds."""
    built = []

    def factory(server):
        client = SimpleNamespace(server=server)
        built.append(client)
        return client

    monkeypatch.setattr(FACTORY, factory)
    return built


def test_collector_reuses_its_client(built_clients):
    collector = JellyfinCollector(make_server(), lambda event: None)

    first = collector._get_media_client()
    second = collector._get_media_client()

    assert first is second
    assert len(built_clients) == 1


def test_collector_rebuilds_client_after_server_edit(built_clients):
    collector = JellyfinCollector(make_server(), lambda event: None)
    collector._get_media_client()

    # Same values: keep the client.
    collector.update_server(make_server())
    collector._get_media_client()
    assert len(built_clients) == 1

    # New URL: build a new client with the new URL.
    collector.update_server(make_server(url="http://b"))
    client = collector._get_media_client()
    assert len(built_clients) == 2
    assert client.server.url == "http://b"


def test_failed_poll_keeps_sessions_and_resets_client(app, built_clients):
    events = []
    collector = JellyfinCollector(
        make_server(), events.append, app=app, batch_callback=events.extend
    )
    collector._get_media_client()
    fake = FakeClient([[session_payload("s1")], ConnectionError("network down"), []])

    sessions = collector._fetch_sessions(fake)
    with collector._event_batch():
        collector._process_sessions(sessions)
    assert [e.event_type for e in events] == ["session_start"]

    # The poll fails: no events, the session stays active, the client resets.
    assert collector._fetch_sessions(fake) is None
    assert collector._client is None
    assert list(collector.active_sessions) == ["s1"]
    assert [e.event_type for e in events] == ["session_start"]

    # A successful empty result ends the session.
    sessions = collector._fetch_sessions(fake)
    with collector._event_batch():
        collector._process_sessions(sessions)
    assert [e.event_type for e in events] == ["session_start", "session_end"]


def test_plex_poll_failure_does_not_end_sessions(app, monkeypatch):
    events = []
    collector = PollingCollector(
        make_server(server_type="plex"),
        events.append,
        app=app,
        batch_callback=events.extend,
    )
    fake = FakeClient([[session_payload("p1")], RuntimeError("timeout"), []])
    monkeypatch.setattr(FACTORY, lambda server: fake)

    collector._poll_sessions()
    collector._poll_sessions()
    assert [e.event_type for e in events] == ["session_start"]

    collector._poll_sessions()
    assert [e.event_type for e in events] == ["session_start", "session_end"]


def event_types(events):
    return [event.event_type for event in events]


def poll(collector, client):
    """Run one poll cycle as the collect loops do."""
    sessions = collector._fetch_sessions(client)
    if sessions is not None:
        with collector._event_batch():
            collector._process_sessions(sessions)
    return sessions


def outage_start():
    """Return a last-success time just beyond the outage limit."""
    return datetime.now(UTC) - POLL_OUTAGE_LIMIT - timedelta(seconds=1)


@pytest.mark.parametrize(
    ("collector_class", "server_type"),
    [
        (JellyfinCollector, "jellyfin"),
        (EmbyCollector, "emby"),
        (PollingCollector, "plex"),
        (AudiobookshelfCollector, "audiobookshelf"),
    ],
)
def test_long_outage_ends_active_sessions(app, collector_class, server_type):
    events = []
    collector = collector_class(
        make_server(server_type=server_type),
        events.append,
        app=app,
        batch_callback=events.extend,
    )
    down = ConnectionError("server down")
    fake = FakeClient(
        [[session_payload("s1")], down, down, down, [session_payload("s1")]]
    )

    poll(collector, fake)
    assert event_types(events) == ["session_start"]

    # A short outage keeps the session.
    assert poll(collector, fake) is None
    assert event_types(events) == ["session_start"]

    # The outage is longer than the limit: the session ends at the time of
    # the last successful poll.
    last_success = outage_start()
    collector.last_successful_poll = last_success
    assert poll(collector, fake) is None
    assert event_types(events) == ["session_start", "session_end"]
    assert events[-1].timestamp == last_success
    assert events[-1].session_id == "s1"

    # More failed polls send no more events.
    assert poll(collector, fake) is None
    assert event_types(events) == ["session_start", "session_end"]

    # The server answers again: the session starts again.
    poll(collector, fake)
    assert event_types(events) == ["session_start", "session_end", "session_start"]
    assert collector.consecutive_failed_polls == 0


def test_outage_end_uses_last_success_for_elapsed_time(app):
    events = []
    collector = AudiobookshelfCollector(
        make_server(server_type="audiobookshelf"),
        events.append,
        app=app,
        batch_callback=events.extend,
    )
    poll(collector, FakeClient([[session_payload("a1")]]))
    last_success = outage_start()
    collector.session_start_times["a1"] = last_success - timedelta(minutes=5)
    collector.last_successful_poll = last_success

    poll(collector, FakeClient([ConnectionError("server down")]))

    end = events[-1]
    assert end.event_type == "session_end"
    # Five minutes of play, not the time of the outage.
    assert end.duration_ms == 5 * 60 * 1000


def test_client_build_failure_counts_as_failed_poll(app, monkeypatch):
    events = []
    collector = JellyfinCollector(
        make_server(), events.append, app=app, batch_callback=events.extend
    )
    collector.active_sessions["s1"] = session_payload("s1")
    collector.last_successful_poll = outage_start()

    def broken_factory(server):
        raise RuntimeError("bad configuration")

    monkeypatch.setattr(FACTORY, broken_factory)

    assert collector._get_media_client() is None
    assert event_types(events) == ["session_end"]
    assert collector.active_sessions == {}


@pytest.mark.parametrize(
    ("long_outage", "expected_events", "expected_sessions"),
    [
        # One failed cycle sends no events and keeps the session.
        (False, [], ["s1"]),
        (True, ["session_end"], []),
    ],
)
def test_jellyfin_loop_failed_cycle(
    app, monkeypatch, long_outage, expected_events, expected_sessions
):
    events = []
    collector = JellyfinCollector(
        make_server(), events.append, app=app, batch_callback=events.extend
    )
    collector.active_sessions["s1"] = session_payload("s1")
    if long_outage:
        collector.last_successful_poll = outage_start()

    def failing_now_playing():
        collector.running = False
        collector._stop_event.set()
        raise ConnectionError("network down")

    client = SimpleNamespace(now_playing=failing_now_playing)
    monkeypatch.setattr(FACTORY, lambda server: client)

    collector.running = True
    collector._collect_loop()

    assert event_types(events) == expected_events
    assert list(collector.active_sessions) == expected_sessions


def test_now_playing_runs_in_app_context(app, monkeypatch):
    collector = AudiobookshelfCollector(
        make_server(server_type="audiobookshelf"),
        lambda event: None,
        app=app,
        batch_callback=lambda events: None,
    )
    fake = FakeClient([[]])

    collector._fetch_sessions(fake)

    assert fake.app_context_seen == [True]


def test_poll_cycle_is_sent_as_one_batch(app):
    batches = []
    single = []
    collector = JellyfinCollector(
        make_server(), single.append, app=app, batch_callback=batches.append
    )

    with collector._event_batch():
        collector._process_sessions([session_payload("s1"), session_payload("s2")])
    with collector._event_batch():
        collector._process_sessions(
            [session_payload("s1", state="paused", position_ms=2000)]
        )

    assert single == []
    assert [[e.event_type for e in batch] for batch in batches] == [
        ["session_start", "session_start"],
        ["session_pause", "session_end"],
    ]
    assert collector.event_count == 4


def test_collector_without_batch_callback_sends_events_one_by_one(app):
    single = []
    collector = JellyfinCollector(make_server(), single.append, app=app)

    with collector._event_batch():
        collector._process_sessions([session_payload("s1"), session_payload("s2")])

    assert [e.event_type for e in single] == ["session_start", "session_start"]


def add_server(app, **values):
    """Store a verified Jellyfin server and return its id."""
    values = {
        "name": "Server",
        "server_type": "jellyfin",
        "url": "http://server",
        "api_key": "k",
        "verified": True,
        **values,
    }
    with app.app_context():
        server = MediaServer(**values)
        db.session.add(server)
        db.session.commit()
        return server.id


class FakeCollector:
    def __init__(self, server):
        self.server = server
        self.updates = []
        self.stopped = False

    def update_server(self, server):
        self.updates.append((server.url, server.api_key))
        self.server = server

    def is_connected(self):
        return True

    def stop(self):
        self.stopped = True

    def start(self):  # pragma: no cover - not started in this test
        pass


def test_monitor_gives_collectors_the_edited_server(app, session, monkeypatch):
    server_id = add_server(app, name="Edit Me", url="http://old", api_key="old-key")

    monitor = WebSocketMonitor(app)
    monkeypatch.setattr(monitor, "_create_collector", FakeCollector)
    monkeypatch.setattr(monitor, "_start_collector", lambda _id, _collector: None)

    with app.app_context():
        monitor._update_collectors()
    collector = monitor.connections[server_id]
    assert collector.server.url == "http://old"

    with app.app_context():
        row = db.session.get(MediaServer, server_id)
        row.url = "http://new"
        row.api_key = "new-key"
        db.session.commit()

    with app.app_context():
        monitor._update_collectors()

    assert monitor.connections[server_id] is collector
    assert collector.updates[-1] == ("http://new", "new-key")
    # The collector thread reads the row after the app context ended.
    assert collector.server.url == "http://new"
    assert collector.server.name == "Edit Me"
    assert collector.server.id == server_id


class BlockingCollector(FakeCollector):
    """Holds its thread until it stops, as a real collector does."""

    def __init__(self, server):
        super().__init__(server)
        self.started = threading.Event()
        self._stop = threading.Event()

    def start(self):
        self.started.set()
        self._stop.wait(5)

    def stop(self):
        super().stop()
        self._stop.set()


def test_monitor_starts_a_collector_for_each_server(app, session, monkeypatch):
    """A pool of 10 workers gave no thread to the servers after the ninth."""
    for i in range(12):
        add_server(app, name=f"Server {i}", url=f"http://srv{i}")

    monitor = WebSocketMonitor(app)
    monkeypatch.setattr(monitor, "_create_collector", BlockingCollector)

    with app.app_context():
        monitor._update_collectors()
    collectors = list(monitor.connections.values())
    try:
        assert len(collectors) == 12
        for collector in collectors:
            assert collector.started.wait(2), collector.server.name
    finally:
        monitor.monitoring = True
        monitor.stop_monitoring()

    assert all(collector.stopped for collector in collectors)
    assert monitor._collector_threads == {}
    assert not any(
        t.name.startswith("activity-collector-") and t.is_alive()
        for t in threading.enumerate()
    )


def test_monitor_stop_waits_for_the_monitor_loop(app, monkeypatch):
    monitor = WebSocketMonitor(app)
    passes = threading.Event()
    monkeypatch.setattr(monitor, "_update_collectors", passes.set)

    monitor.start_monitoring()
    assert passes.wait(2)
    loop_thread = monitor._monitor_thread
    monitor.stop_monitoring()

    assert not loop_thread.is_alive()

    # A restart runs a new loop.
    passes.clear()
    monitor.start_monitoring()
    assert passes.wait(2)
    monitor.stop_monitoring()


def test_collector_stopped_before_start_does_not_run(app):
    collector = PollingCollector(make_server(server_type="plex"), lambda e: None)
    loops = []
    collector._collect_loop = lambda: loops.append(1)

    collector.stop()
    collector.start()

    assert loops == []
    assert collector.running is False


class SlowCollector(FakeCollector):
    """Holds its thread until the test releases it, also after stop().

    This is a collector in a slow poll: it sees the stop only after the poll.
    """

    def __init__(self, server):
        super().__init__(server)
        self.started = threading.Event()
        self.release = threading.Event()

    def start(self):
        self.started.set()
        self.release.wait(5)


def test_type_change_waits_for_the_old_collector_thread(app, session, monkeypatch):
    monkeypatch.setattr(monitor_module, "COLLECTOR_RESTART_JOIN_TIMEOUT", 0.05)
    server_id = add_server(app)

    monitor = WebSocketMonitor(app)
    created = []

    def create(server):
        collector = SlowCollector(server)
        created.append(collector)
        return collector

    monkeypatch.setattr(monitor, "_create_collector", create)
    try:
        with app.app_context():
            monitor._update_collectors()
        old = created[0]
        assert old.started.wait(2)
        old_thread = monitor._collector_threads[server_id]

        with app.app_context():
            db.session.get(MediaServer, server_id).server_type = "emby"
            db.session.commit()
        with app.app_context():
            monitor._update_collectors()

        # The old thread still runs: no second collector in this pass, and
        # the monitor keeps the old handle.
        assert old.stopped
        assert len(created) == 1
        assert server_id not in monitor.connections
        assert monitor._collector_threads[server_id] is old_thread

        # The old thread ends. The next pass joins it and starts a new one.
        old.release.set()
        with app.app_context():
            monitor._update_collectors()
        assert len(created) == 2
        assert monitor.connections[server_id] is created[1]
        assert not old_thread.is_alive()
        assert monitor._collector_threads[server_id] is not old_thread
        assert created[1].started.wait(2)
        alive = [
            t
            for t in threading.enumerate()
            if t.name == f"activity-collector-{server_id}" and t.is_alive()
        ]
        assert len(alive) == 1
    finally:
        for collector in created:
            collector.release.set()
        monitor.monitoring = True
        monitor.stop_monitoring()


def test_stop_keeps_handles_of_collectors_that_still_run(app, session, monkeypatch):
    monkeypatch.setattr(monitor_module, "COLLECTOR_JOIN_TIMEOUT", 0.05)
    monkeypatch.setattr(monitor_module, "COLLECTOR_RESTART_JOIN_TIMEOUT", 0.05)
    server_id = add_server(app)

    monitor = WebSocketMonitor(app)
    created = []

    def create(server):
        collector = SlowCollector(server)
        created.append(collector)
        return collector

    monkeypatch.setattr(monitor, "_create_collector", create)
    try:
        with app.app_context():
            monitor._update_collectors()
        assert created[0].started.wait(2)
        monitor.monitoring = True
        monitor.stop_monitoring()

        # The thread did not stop in time. The monitor keeps its handle, and
        # a new start does not start a second collector while it runs.
        assert server_id in monitor._collector_threads
        with app.app_context():
            monitor._update_collectors()
        assert len(created) == 1

        created[0].release.set()
        with app.app_context():
            monitor._update_collectors()
        assert len(created) == 2
    finally:
        for collector in created:
            collector.release.set()
        monitor.monitoring = True
        monitor.stop_monitoring()
