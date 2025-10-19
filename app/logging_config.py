import logging.config
import os
import sys
from pathlib import Path

LOG_LEVEL = os.getenv("LOG_LEVEL", "WARNING").upper()

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,  # keep libs like werkzeug quiet only if you want
    "formatters": {
        "default": {
            "format": "%(asctime)s  %(levelname)-8s  %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "stream": sys.stdout,
            "formatter": "default",
            "level": LOG_LEVEL,
        },
        # ○ add a rotating-file handler if you fancy
        # "file": {
        #     "class": "logging.handlers.RotatingFileHandler",
        #     "filename": str(Path(__file__).resolve().parent.parent / "logs" / "wizarr.log"),
        #     "maxBytes": 5_000_000,
        #     "backupCount": 3,
        #     "formatter": "default",
        #     "level": LOG_LEVEL,
        # },
    },
    "root": {
        "handlers": ["console"],
        "level": LOG_LEVEL,
    },
    "loggers": {
        "app.services.media.romm": {
            "level": "DEBUG",
            "handlers": ["console"],
            "propagate": False,
        },
        "wizarr.api": {
            "level": "INFO",
            "handlers": ["console"],
            "propagate": False,
        },
        "alembic": {
            "level": "ERROR",
            "handlers": ["console"],
            "propagate": False,
        },
        "alembic.runtime.migration": {
            "level": "ERROR",
            "handlers": ["console"],
            "propagate": False,
        },
        "sqlalchemy": {
            "level": "ERROR",
            "handlers": ["console"],
            "propagate": False,
        },
        "app.services.wizard_seed": {
            "level": "WARNING",
            "handlers": ["console"],
            "propagate": False,
        },
        "app.services.wizard_migration": {
            "level": "WARNING",
            "handlers": ["console"],
            "propagate": False,
        },
    },
}


def configure_logging() -> None:
    """Call this once at start-up."""
    if "file" in LOGGING_CONFIG.get("handlers", {}):
        log_path = Path(LOGGING_CONFIG["handlers"]["file"]["filename"])
        log_path.parent.mkdir(parents=True, exist_ok=True)

    logging.config.dictConfig(LOGGING_CONFIG)
