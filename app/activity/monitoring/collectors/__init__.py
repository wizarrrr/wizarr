"""
Activity collectors for different media server types.

Provides specialized collectors for real-time activity monitoring:
- PlexCollector: Uses PlexAPI AlertListener for real-time events
- JellyfinCollector: Uses WebSocket API for real-time events
- EmbyCollector: Uses WebSocket API for real-time events
- AudiobookshelfCollector: Uses Socket.IO for real-time events
- PollingCollector: Fallback polling for other server types
"""

from .audiobookshelf import AudiobookshelfCollector
from .emby import EmbyCollector
from .jellyfin import JellyfinCollector
from .plex import PlexCollector
from .polling import PollingCollector

__all__ = [
    "PlexCollector",
    "JellyfinCollector",
    "EmbyCollector",
    "AudiobookshelfCollector",
    "PollingCollector",
]
