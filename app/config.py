# config.py
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

class BaseConfig:
    # Flask
    TEMPLATES_AUTO_RELOAD = True
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-override-me")
    # Sessions
    SESSION_TYPE = "filesystem"
    SESSION_FILE_DIR = BASE_DIR / "database" / "sessions"
    # Babel / i18n
    LANGUAGES = {
        "en": "english", "de": "german", "zh": "chinese", "fr": "french",
        "sv": "swedish", "pt": "portuguese", "pt_BR": "portuguese",
        "lt": "lithuanian", "es": "spanish", "ca": "catalan",
        "pl": "polish",
    }
    BABEL_DEFAULT_LOCALE = "en"
    BABEL_TRANSLATION_DIRECTORIES = str(BASE_DIR / "translations")
    # Scheduler
    SCHEDULER_API_ENABLED = True
    # SQLAlchemy
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{BASE_DIR / 'database' / 'database.db'}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

class DevelopmentConfig(BaseConfig):
    DEBUG = True

class ProductionConfig(BaseConfig):
    DEBUG = False