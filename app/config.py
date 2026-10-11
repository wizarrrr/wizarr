# config.py
import json
import os
import secrets
from pathlib import Path
from typing import ClassVar

from dotenv import load_dotenv

from app.utils.session_cache import RobustFileSystemCache

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# Initialize session cache at module level so Flask-Session can access it

# Ensure database directory exists
# Use /data/database for container deployments, fall back to local for development


if Path("/data").exists():
    DATABASE_DIR = Path("/data/database")
else:
    DATABASE_DIR = BASE_DIR / "database"
DATABASE_DIR.mkdir(exist_ok=True)

SESSION_CACHELIB = RobustFileSystemCache(
    str(DATABASE_DIR / "sessions"),
    threshold=1000,  # Max files before cleanup
    default_timeout=86400,  # 24 hours
    mode=0o600,  # Restrict file permissions
)

# Define secrets file location next to database
SECRETS_FILE = DATABASE_DIR / "secrets.json"


def generate_secret_key():
    """Generate a secure random secret key."""
    return secrets.token_hex(32)


def load_secrets():
    """Load secrets from the secrets file."""
    if not SECRETS_FILE.exists():
        return {}

    try:
        with SECRETS_FILE.open() as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {}


def save_secrets(secrets_dict):
    """Save secrets to the secrets file."""
    # Ensure database directory exists
    DATABASE_DIR.mkdir(exist_ok=True)

    with SECRETS_FILE.open("w") as f:
        json.dump(secrets_dict, f, indent=2)


def get_or_create_secret(key, generator_func):
    """Get a secret from the secrets file or create it if it doesn't exist."""
    secrets_dict = load_secrets()

    if key not in secrets_dict:
        secrets_dict[key] = generator_func()
        save_secrets(secrets_dict)

    return secrets_dict[key]


class BaseConfig:
    # Flask
    SECRET_KEY = get_or_create_secret("SECRET_KEY", generate_secret_key)
    # Sessions
    SESSION_TYPE = "cachelib"  # Changed from 'filesystem' to 'cachelib'
    SESSION_CACHELIB = SESSION_CACHELIB  # Reference the module-level cache

    # Babel / i18n
    LANGUAGES: ClassVar[dict[str, str]] = {
        "en": "English",
        "ca": "Catalan",
        "cs": "Czech",
        "da": "Danish",
        "de": "German",
        "es": "Spanish",
        "fa": "Persian",
        "fr": "French",
        "gsw": "Swiss German",
        "he": "Hebrew",
        "hr": "Croatian",
        "hu": "Hungarian",
        "is": "Icelandic",
        "it": "Italian",
        "lt": "Lithuanian",
        "nb_NO": "Norwegian Bokmål",
        "nl": "Dutch",
        "pl": "Polish",
        "pt": "Portuguese",
        "pt_BR": "Portuguese (Brazil)",
        "ro": "Romanian",
        "ru": "Russian",
        "sv": "Swedish",
        "zh_Hans": "Chinese (Simplified)",
        "zh_Hant": "Chinese (Traditional)",
    }
    BABEL_DEFAULT_LOCALE = "en"
    BABEL_TRANSLATION_DIRECTORIES = str(BASE_DIR / "app" / "translations")
    # Allow forcing a specific language via environment variable
    FORCE_LANGUAGE = os.getenv("FORCE_LANGUAGE")
    # Scheduler. The REST API stays off for security. The job store is in
    # memory: the jobs keep a reference to the app, so they cannot be saved.
    SCHEDULER_API_ENABLED = False
    SCHEDULER_JOB_DEFAULTS: ClassVar[dict] = {
        "coalesce": True,
        "max_instances": 1,
        "misfire_grace_time": 300,
    }
    # Compression (Flask-Compress). app/static_assets.py applies it only to
    # static files. Do NOT compress text/html: HTML responses contain CSRF
    # tokens and reflected input, and compression makes them open to the
    # BREACH attack.
    COMPRESS_REGISTER = False
    COMPRESS_MIMETYPES: ClassVar[list[str]] = [
        "text/css",
        "text/javascript",
        "application/javascript",
        "image/svg+xml",
        "application/json",
        "application/manifest+json",
    ]
    # SQLAlchemy
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{DATABASE_DIR / 'database.db'}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # SQLite engine options for concurrent write support
    SQLALCHEMY_ENGINE_OPTIONS: ClassVar[dict] = {
        "connect_args": {
            "timeout": 30,  # 30 second timeout for lock waits
            "check_same_thread": False,  # Allow multi-threaded access
        },
        # No pool_pre_ping: a SQLite connection is a local file, so it does not
        # drop. A ping only adds one "SELECT 1" to each checkout.
        "pool_recycle": 3600,  # Recycle connections after 1 hour
    }


class DevelopmentConfig(BaseConfig):
    DEBUG = True
    # Check the template files for changes on each render (development only).
    TEMPLATES_AUTO_RELOAD = True


class ProductionConfig(BaseConfig):
    DEBUG = False
