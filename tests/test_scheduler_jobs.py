"""Tests for the scheduled jobs and the scheduler configuration."""

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from app.config import BaseConfig, DevelopmentConfig, ProductionConfig
from app.extensions import init_scheduler, register_scheduled_jobs, scheduler
from app.models import LDAPConfiguration
from app.tasks.ldap_sync import sync_ldap_users
from app.tasks.maintenance import optimize_sqlite_database


class FakeScheduler:
    def __init__(self):
        self.jobs = {}

    def add_job(self, **kwargs):
        self.jobs[kwargs.pop("id")] = kwargs


def _registered_jobs(app):
    fake = FakeScheduler()
    now = datetime(2026, 1, 1, tzinfo=UTC)
    register_scheduled_jobs(app, fake, now=now)
    return fake.jobs, now


def test_all_maintenance_jobs_are_registered(app, session):
    # The LDAP sync job is registered also when LDAP is not configured.
    assert LDAPConfiguration.query.count() == 0

    jobs, _ = _registered_jobs(app)

    assert set(jobs) == {
        "check_expiring",
        "fetch_manifest",
        "sync_ldap_users",
        "sqlite_optimize",
    }
    for job in jobs.values():
        assert job["max_instances"] == 1
        assert job["coalesce"] is True
        assert job["replace_existing"] is True
        assert job["args"] == [app]
    assert jobs["sync_ldap_users"]["func"] is sync_ldap_users
    assert jobs["sync_ldap_users"]["trigger"] == "interval"


def test_jobs_have_sensible_first_run_times(app):
    jobs, now = _registered_jobs(app)

    # The manifest fetch no longer blocks startup: it runs soon after start.
    assert jobs["fetch_manifest"]["next_run_time"] - now <= timedelta(minutes=1)
    assert jobs["fetch_manifest"]["hours"] == 24
    assert jobs["check_expiring"]["next_run_time"] == now + timedelta(minutes=1)
    assert jobs["sync_ldap_users"]["next_run_time"] == now + timedelta(minutes=2)
    # The startup thread runs the first optimize, so the job waits one day.
    assert "next_run_time" not in jobs["sqlite_optimize"]
    assert jobs["sqlite_optimize"]["hours"] == 24


def test_ldap_sync_returns_early_when_ldap_is_disabled(app, session):
    with patch("app.services.ldap.user_sync.list_ldap_users") as list_users:
        sync_ldap_users(app)

    list_users.assert_not_called()


def test_disable_flag_keeps_the_scheduler_stopped(app, monkeypatch):
    monkeypatch.setenv("WIZARR_DISABLE_SCHEDULER", "true")

    with patch.object(scheduler, "start") as start:
        assert init_scheduler(app) is False

    start.assert_not_called()


def test_scheduler_configuration():
    assert not hasattr(BaseConfig, "SCHEDULER_JOBSTORE_URL")
    assert BaseConfig.SCHEDULER_API_ENABLED is False
    assert BaseConfig.SCHEDULER_JOB_DEFAULTS["coalesce"] is True
    assert BaseConfig.SCHEDULER_JOB_DEFAULTS["max_instances"] == 1


def test_sqlite_engine_has_no_pre_ping():
    assert "pool_pre_ping" not in BaseConfig.SQLALCHEMY_ENGINE_OPTIONS


def test_template_auto_reload_is_for_development_only():
    assert DevelopmentConfig.TEMPLATES_AUTO_RELOAD is True
    assert getattr(ProductionConfig, "TEMPLATES_AUTO_RELOAD", None) is None


def test_sqlite_optimize_runs_without_error(app, caplog):
    optimize_sqlite_database(app)

    assert "PRAGMA optimize failed" not in caplog.text


def test_sqlite_optimize_sends_the_pragmas(app):
    statements = []

    class Connection:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def exec_driver_sql(self, sql):
            statements.append(sql)

        def commit(self):
            statements.append("COMMIT")

    with app.app_context():
        from app.extensions import db

        with patch.object(db.engine, "connect", return_value=Connection()):
            optimize_sqlite_database(app)

    assert statements == [
        "PRAGMA analysis_limit=400",
        "PRAGMA optimize=0x10002",
        "COMMIT",
    ]
