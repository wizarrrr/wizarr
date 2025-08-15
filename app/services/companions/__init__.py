"""
Companion app integration system.

This module provides a modular system for integrating with companion apps
like Ombi, Overseerr, and Audiobookrequest. Each companion type has its own
client implementation following a common interface.
"""

from .audiobookrequest import AudiobookrequestClient
from .base import CompanionClient
from .ombi import OmbiClient
from .overseerr import OverseerrClient

__all__ = [
    "CompanionClient",
    "get_companion_client",
    "register_companion_client",
    "list_companion_types",
]

# Registry of companion client implementations
_companion_registry: dict[str, type[CompanionClient]] = {}


def register_companion_client(connection_type: str):
    """Decorator to register a companion client implementation."""

    def decorator(cls: type[CompanionClient]):
        _companion_registry[connection_type] = cls
        return cls

    return decorator


def get_companion_client(connection_type: str) -> type[CompanionClient]:
    """Get the companion client class for the given connection type."""
    if connection_type not in _companion_registry:
        raise ValueError(f"Unknown companion type: {connection_type}")
    return _companion_registry[connection_type]


def list_companion_types() -> list[tuple[str, str]]:
    """Return list of (value, label) tuples for all registered companion types."""
    return [
        ("ombi", "Ombi"),
        ("overseerr", "Overseerr/Jellyseerr (Info Only)"),
        ("audiobookrequest", "Audiobookrequest"),
    ]


# Register all companion clients
register_companion_client("ombi")(OmbiClient)
register_companion_client("overseerr")(OverseerrClient)
register_companion_client("audiobookrequest")(AudiobookrequestClient)
