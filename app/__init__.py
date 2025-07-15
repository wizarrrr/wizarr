import os

from flask import Flask

from .config import DevelopmentConfig
from .error_handlers import register_error_handlers
from .extensions import init_extensions
from .logging_config import configure_logging
from .middleware import require_onboarding


def create_app(config_object=DevelopmentConfig):
    print("Creating app")
    print(f"Wizarr version: 🧙‍♂️ {os.getenv('APP_VERSION', 'dev')}")
    configure_logging()  # ① logging is ready     # ② crash fast if mis-configured

    app = Flask(__name__)
    app.config.from_object(config_object)

    # 1. extensions
    print("Initialising extensions")
    init_extensions(app)
    print("Finished Initialising app")

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

    # Register custom Jinja filters
    from .jinja_filters import register_filters

    register_filters(app)

    app.before_request(require_onboarding)

    # ─── Seed default wizard steps (no-ops if already present or in TESTING) ───
    with app.app_context():
        try:
            from .services.wizard_seed import import_default_wizard_steps

            import_default_wizard_steps()
        except Exception as exc:
            # Non-fatal – log and continue startup to avoid blocking the app
            app.logger.warning("Wizard step bootstrap failed: %s", exc)

        # ─── Run wizard migrations (update external_url references) ───
        try:
            from .services.wizard_migration import run_wizard_migrations

            migration_success = run_wizard_migrations()
            if not migration_success:
                app.logger.warning(
                    "Wizard step migrations had issues - check logs for details"
                )
        except Exception as exc:
            # Non-fatal – log and continue startup to avoid blocking the app
            app.logger.warning("Wizard step migration failed: %s", exc)

    return app
