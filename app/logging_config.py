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
        # Note: Rotating file handler can be added if persistent logging is needed.
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

    # Configure structlog to use standard library logging
    # This ensures structlog respects our logging level configuration
    import structlog

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.filter_by_level,  # Filter by log level first
            structlog.stdlib.add_logger_name,  # Add logger name
            structlog.stdlib.add_log_level,  # Add log level
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            # Render to plain text, not JSON dict
            structlog.dev.ConsoleRenderer()
            if sys.stdout.isatty()
            else structlog.processors.JSONRenderer(),
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
