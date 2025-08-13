# config.py
import json
import os
import secrets
from pathlib import Path

from dotenv import load_dotenv

from app.utils.session_cache import RobustFileSystemCache

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# Initialize session cache at module level so Flask-Session can access it

# Ensure database directory exists
# Use /data/database for container deployments, fall back to local for development


if os.path.exists("/data"):
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
        with open(SECRETS_FILE) as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {}


def save_secrets(secrets_dict):
    """Save secrets to the secrets file."""
    # Ensure database directory exists
    DATABASE_DIR.mkdir(exist_ok=True)

    with open(SECRETS_FILE, "w") as f:
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
    TEMPLATES_AUTO_RELOAD = True
    SECRET_KEY = get_or_create_secret("SECRET_KEY", generate_secret_key)
    # Sessions
    SESSION_TYPE = "cachelib"  # Changed from 'filesystem' to 'cachelib'
    SESSION_CACHELIB = SESSION_CACHELIB  # Reference the module-level cache

    # Babel / i18n
    LANGUAGES = {
        "en": "english",
        "de": "german",
        "zh": "chinese",
        "fr": "french",
        "sv": "swedish",
        "pt": "portuguese",
        "pt_BR": "portuguese",
        "lt": "lithuanian",
        "es": "spanish",
        "ca": "catalan",
        "pl": "polish",
    }
    BABEL_DEFAULT_LOCALE = "en"
    BABEL_TRANSLATION_DIRECTORIES = str(BASE_DIR / "app" / "translations")
    # Scheduler
    SCHEDULER_API_ENABLED = True
    # SQLAlchemy
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{DATABASE_DIR / 'database.db'}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False


class DevelopmentConfig(BaseConfig):
    DEBUG = True


class ProductionConfig(BaseConfig):
    DEBUG = False
