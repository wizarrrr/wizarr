import logging, os
from urllib.parse import urlparse

REQUIRED_VARS = ("APP_URL",)

def validate_env() -> None:
    """Exit early if critical environment variables are missing or malformed."""
    missing = [v for v in REQUIRED_VARS if not os.getenv(v)]
    if missing:
        logging.critical("Missing required environment vars: %s", ", ".join(missing))
        raise SystemExit(1)

    # basic sanity check for APP_URL
    url = os.getenv("APP_URL", "")
    parsed = urlparse(url)
    if not (parsed.scheme and parsed.netloc):
        logging.critical("APP_URL looks invalid: %s", url)
        raise SystemExit(1)
