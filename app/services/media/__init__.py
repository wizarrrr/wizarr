"""Media service subpackage.

This package provides unified access to various media server types through
a common client interface. Each client implements the MediaClient abstract
base class and is automatically registered for use by the service layer.
"""

# Import clients to trigger registration
from .audiobookshelf import AudiobookshelfClient  # noqa: F401
from .emby import EmbyClient  # noqa: F401
from .jellyfin import JellyfinClient  # noqa: F401
from .kavita import KavitaClient  # noqa: F401
from .komga import KomgaClient  # noqa: F401
from .navidrome import NavidromeClient  # noqa: F401
from .romm import RommClient  # noqa: F401
