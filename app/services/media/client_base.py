from abc import ABC, abstractmethod
from app.extensions import db
from app.models import Settings

# Registry for media client implementations (e.g. Plex, Jellyfin)
CLIENTS = {}

def register_media_client(name: str):
    """Decorator to register a MediaClient under a given server_type name."""
    def decorator(cls):
        CLIENTS[name] = cls
        return cls
    return decorator

class MediaClient(ABC):
    """
    Abstract base class for media clients (Plex, Jellyfin).
    Loads server URL and API token from Settings.
    """
    def __init__(self, url_key: str = "server_url", token_key: str = "api_key"):
        self.url = (
            db.session.query(Settings.value)
            .filter_by(key=url_key)
            .scalar()
        )
        self.token = (
            db.session.query(Settings.value)
            .filter_by(key=token_key)
            .scalar()
        )

    @abstractmethod
    def libraries(self):
        raise NotImplementedError

    @abstractmethod
    def create_user(self, *args, **kwargs):
        raise NotImplementedError

    @abstractmethod
    def update_user(self, *args, **kwargs):
        raise NotImplementedError

    @abstractmethod
    def delete_user(self, *args, **kwargs):
        raise NotImplementedError

    @abstractmethod
    def get_user(self, *args, **kwargs):
        raise NotImplementedError