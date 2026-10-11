import runpy
from pathlib import Path

CONFIG_PATH = Path(__file__).resolve().parents[1] / "gunicorn.conf.py"


def test_gunicorn_uses_one_threaded_worker_by_default(monkeypatch):
    monkeypatch.delenv("GUNICORN_WORKERS", raising=False)
    monkeypatch.delenv("GUNICORN_THREADS", raising=False)

    config = _load_config(monkeypatch)

    assert config["workers"] == 1
    assert config["threads"] == 4
    assert config["worker_class"] == "gthread"


def test_gunicorn_worker_and_thread_counts_remain_configurable(monkeypatch):
    monkeypatch.setenv("GUNICORN_WORKERS", "2")
    monkeypatch.setenv("GUNICORN_THREADS", "6")

    config = _load_config(monkeypatch)

    assert config["workers"] == 2
    assert config["threads"] == 6


def _load_config(monkeypatch):
    # Restore the environment variable that the config file sets.
    monkeypatch.setenv("WIZARR_GUNICORN_MASTER_PID", "")
    return runpy.run_path(str(CONFIG_PATH))


def test_gunicorn_master_does_not_import_the_app(monkeypatch, capsys):
    import os
    import sys
    from types import SimpleNamespace

    monkeypatch.delitem(sys.modules, "run", raising=False)
    config = _load_config(monkeypatch)

    config["when_ready"](SimpleNamespace())

    assert "run" not in sys.modules
    assert os.environ["WIZARR_GUNICORN_MASTER_PID"] == str(os.getpid())
    assert "ready" in capsys.readouterr().out


def test_worker_exit_stops_the_scheduler(monkeypatch):
    from types import SimpleNamespace
    from unittest.mock import patch

    config = _load_config(monkeypatch)
    worker = SimpleNamespace(pid=1234, age=1)

    with patch("app.background.shutdown_background_services") as shutdown:
        config["worker_exit"](SimpleNamespace(), worker)

    shutdown.assert_called_once_with()


def test_post_fork_without_preload_does_nothing(monkeypatch):
    from types import SimpleNamespace
    from unittest.mock import patch

    config = _load_config(monkeypatch)
    server = SimpleNamespace(cfg=SimpleNamespace(preload_app=False))

    with patch("app.background.on_worker_fork") as on_fork:
        config["post_fork"](server, SimpleNamespace(pid=1))

    on_fork.assert_not_called()


def test_post_fork_with_preload_prepares_the_worker(monkeypatch):
    from types import SimpleNamespace
    from unittest.mock import patch

    config = _load_config(monkeypatch)
    wsgi_app = object()
    server = SimpleNamespace(
        cfg=SimpleNamespace(preload_app=True),
        app=SimpleNamespace(wsgi=lambda: wsgi_app),
    )

    with patch("app.background.on_worker_fork") as on_fork:
        config["post_fork"](server, SimpleNamespace(pid=1))

    on_fork.assert_called_once_with(wsgi_app)
