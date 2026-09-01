import runpy
from pathlib import Path

CONFIG_PATH = Path(__file__).resolve().parents[1] / "gunicorn.conf.py"


def test_gunicorn_uses_one_threaded_worker_by_default(monkeypatch):
    monkeypatch.delenv("GUNICORN_WORKERS", raising=False)
    monkeypatch.delenv("GUNICORN_THREADS", raising=False)

    config = runpy.run_path(str(CONFIG_PATH))

    assert config["workers"] == 1
    assert config["threads"] == 4
    assert config["worker_class"] == "gthread"


def test_gunicorn_worker_and_thread_counts_remain_configurable(monkeypatch):
    monkeypatch.setenv("GUNICORN_WORKERS", "2")
    monkeypatch.setenv("GUNICORN_THREADS", "6")

    config = runpy.run_path(str(CONFIG_PATH))

    assert config["workers"] == 2
    assert config["threads"] == 6
