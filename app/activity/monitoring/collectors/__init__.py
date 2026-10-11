"""
Activity collectors for different media server types.

Provides specialized collectors for activity monitoring:
- JellyfinCollector: Uses WebSocket API for real-time events
- EmbyCollector: Uses WebSocket API for real-time events
- AudiobookshelfCollector: Uses REST API polling for activity monitoring
- PollingCollector: Generic polling collector used for Plex and other servers
"""

from .audiobookshelf import AudiobookshelfCollector
from .emby import EmbyCollector
from .jellyfin import JellyfinCollector
from .polling import PollingCollector

__all__ = [
    "AudiobookshelfCollector",
    "EmbyCollector",
    "JellyfinCollector",
    "PollingCollector",
]
