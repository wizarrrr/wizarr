from flask import Flask
from .config import DevelopmentConfig
from .extensions import init_extensions, db
from .middleware import require_onboarding
from .models import Invitation, Settings, User, Notification
import os
from .error_handlers import register_error_handlers
from .logging_config import configure_logging


def create_app(config_object=DevelopmentConfig):
    print("Creating app")
    print(f"Wizarr version: 🧙‍♂️ {os.getenv("APP_VERSION", "dev")}") 
    configure_logging()   # ① logging is ready     # ② crash fast if mis-configured
    
    app = Flask(__name__)
    app.config.from_object(config_object)

    # 1. extensions
    print("Initialising extensions")
    init_extensions(app)
    print("Finished Initialising app")
    from .models import Invitation, Settings, User, Notification
    from .tasks import maintenance

    
    # 2. blueprints
    from .blueprints import all_blueprints
    for bp in all_blueprints:
        app.register_blueprint(bp)

   # # 3. database tables (safe=True avoids clobbering prod data)
  #  with app.app_context():
     #   db.create_all()

    from .context_processors import inject_server_name
    app.context_processor(inject_server_name)

    register_error_handlers(app)
    
    app.before_request(require_onboarding)
    return app
