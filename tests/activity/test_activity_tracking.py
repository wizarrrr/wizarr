import re
from unittest.mock import Mock, patch

import pytest

from app.activity.tracking import (
    ACTIVITY_TRACKING_SETTING,
    is_activity_tracking_enabled,
    reconcile_activity_tracking,
    set_activity_tracking_enabled,
)
from app.models import Settings
from app.tasks.activity import ACTIVITY_JOB_IDS, activity_monitoring_heartbeat_task


class FakeScheduler:
    def __init__(self, job_ids=()):
        self.jobs = {job_id: object() for job_id in job_ids}

    def add_job(self, **kwargs):
        job_id = kwargs.pop("id")
        self.jobs[job_id] = kwargs

    def get_job(self, job_id):
        return self.jobs.get(job_id)

    def remove_job(self, job_id):
        self.jobs.pop(job_id)


def test_activity_tracking_is_enabled_by_default(app, session):
    with app.app_context():
        assert is_activity_tracking_enabled() is True


def test_activity_tracking_setting_is_persistent(app, session):
    with app.app_context():
        set_activity_tracking_enabled(False)

        setting = Settings.query.filter_by(key=ACTIVITY_TRACKING_SETTING).one()
        assert setting.value == "false"
        assert is_activity_tracking_enabled() is False

        set_activity_tracking_enabled(True)

        assert setting.value == "true"
        assert is_activity_tracking_enabled() is True


def test_disabled_tracking_stops_monitor_and_removes_jobs(app, session):
    scheduler = FakeScheduler(ACTIVITY_JOB_IDS)

    with app.app_context():
        set_activity_tracking_enabled(False)

    with patch("app.activity.tracking.stop_activity_tracking") as stop_tracking:
        enabled = reconcile_activity_tracking(app, scheduler)

    assert enabled is False
    stop_tracking.assert_called_once_with(app)
    assert all(scheduler.get_job(job_id) is None for job_id in ACTIVITY_JOB_IDS)


def test_enabled_tracking_starts_monitor_and_registers_jobs(app, session):
    scheduler = FakeScheduler()

    with patch("app.activity.tracking.start_activity_tracking") as start_tracking:
        enabled = reconcile_activity_tracking(app, scheduler)

    assert enabled is True
    start_tracking.assert_called_once_with(app, delay_seconds=0)
    assert all(scheduler.get_job(job_id) is not None for job_id in ACTIVITY_JOB_IDS)


@pytest.mark.parametrize("enabled", [True, False])
def test_activity_settings_shows_tracking_state(admin_client, enabled):
    set_activity_tracking_enabled(enabled)

    response = admin_client.get("/activity/settings", headers={"HX-Request": "true"})

    assert response.status_code == 200
    toggle = re.search(
        r'<input id="activity-tracking-enabled"[^>]*>', response.get_data(as_text=True)
    )
    assert toggle is not None
    assert ("checked" in toggle.group(0)) is enabled


@pytest.mark.parametrize(
    ("form", "enabled", "message"),
    [
        # The browser sends no value for an unchecked checkbox.
        ({}, False, "Activity tracking is disabled"),
        ({"activity_tracking_enabled": "true"}, True, "Activity tracking is enabled"),
    ],
)
def test_activity_settings_sets_tracking(admin_client, form, enabled, message):
    set_activity_tracking_enabled(not enabled)

    response = admin_client.post(
        "/activity/settings",
        data={"action": "set_tracking", **form},
        headers={"HX-Request": "true"},
    )

    assert response.status_code == 200
    assert is_activity_tracking_enabled() is enabled
    assert message in response.get_data(as_text=True)


def test_disabled_tracking_heartbeat_does_not_restart_monitor(
    app, session, monkeypatch
):
    monitor = Mock()
    monitor.monitoring = False
    monkeypatch.setitem(app.extensions, "activity_monitor", monitor)

    with app.app_context():
        set_activity_tracking_enabled(False)

    assert activity_monitoring_heartbeat_task(app) is False
    monitor.start_monitoring.assert_not_called()
