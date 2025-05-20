import logging.config, os, sys
from pathlib import Path

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,      # keep libs like werkzeug quiet only if you want
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
        #     "filename": Path(__file__).resolve().parent.parent / "logs" / "app.log",
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
}

def configure_logging() -> None:
    """Call this once at start-up."""
    logging.config.dictConfig(LOGGING_CONFIG)
