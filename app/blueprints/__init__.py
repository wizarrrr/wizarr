from .admin.routes import admin_bp
from .admin_accounts.routes import admin_accounts_bp
from .api.api_routes import api_bp
from .api.status import status_bp
from .api_keys.routes import api_keys_bp
from .audiobookshelf.routes import abs_bp
from .auth.routes import auth_bp
from .connections.routes import connections_bp
from .emby.routes import emby_bp
from .jellyfin.routes import jellyfin_bp
from .kavita.routes import kavita_bp
from .komga.routes import komga_bp
from .media_servers.routes import media_servers_bp
from .notifications.routes import notify_bp
from .plex.routes import plex_bp
from .public.routes import public_bp
from .settings.routes import settings_bp
from .setup.routes import setup_bp
from .webauthn.routes import webauthn_bp
from .wizard.routes import wizard_bp
from .wizard_admin.routes import wizard_admin_bp

# NOTE: Server-specific join routes (jellyfin_bp, emby_bp, abs_bp, kavita_bp, komga_bp)
# are now deprecated in favor of the unified invitation processor.
# They are kept registered for backward compatibility and admin/scan functions.

all_blueprints = (
    public_bp,
    wizard_bp,
    admin_bp,
    auth_bp,
    settings_bp,
    connections_bp,
    setup_bp,
    plex_bp,
    notify_bp,
    jellyfin_bp,
    emby_bp,
    abs_bp,
    kavita_bp,
    komga_bp,
    api_bp,
    status_bp,
    api_keys_bp,
    media_servers_bp,
    wizard_admin_bp,
    admin_accounts_bp,
    webauthn_bp,
)
