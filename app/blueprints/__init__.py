from .admin.routes import admin_bp
from .auth.routes  import auth_bp
from .settings.routes import settings_bp
from .setup.routes    import setup_bp
from .public.routes  import public_bp
from .wizard.routes  import wizard_bp
from .plex.routes import plex_bp
from .notifications.routes import notify_bp

all_blueprints = (public_bp, wizard_bp, admin_bp, auth_bp,
                  settings_bp, setup_bp, plex_bp, notify_bp)