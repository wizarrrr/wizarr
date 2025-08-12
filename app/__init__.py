import os

from flask import Flask

from .config import DevelopmentConfig
from .error_handlers import register_error_handlers
from .extensions import init_extensions
from .logging_config import configure_logging
from .middleware import require_onboarding
from .startup_logger import startup_logger


def create_app(config_object=DevelopmentConfig):
    # Display welcome and start startup sequence (master process only)
    startup_logger.welcome(os.getenv("APP_VERSION", "dev"))
    startup_logger.start_sequence(total_steps=8)

    # Step 1: Configure logging
    startup_logger.step("Configuring logging system", "📝")
    configure_logging()  # ① logging is ready     # ② crash fast if mis-configured

    # Step 2: Create Flask application
    startup_logger.step("Creating Flask application", "🌐")
    app = Flask(__name__)
    app.config.from_object(config_object)

    # Step 3: Initialize extensions
    startup_logger.step("Initializing extensions", "🔧")
    init_extensions(app)

    # Step 4: Register blueprints
    startup_logger.step("Registering blueprints", "🛤️")
    from .blueprints import all_blueprints

    for bp in all_blueprints:
        app.register_blueprint(bp)

    # Step 5: Setup context processors and filters
    startup_logger.step("Configuring request processing", "⚙️")
    from .context_processors import inject_server_name

    app.context_processor(inject_server_name)
    register_error_handlers(app)

    # Register custom Jinja filters
    from .jinja_filters import register_filters

    register_filters(app)
    app.before_request(require_onboarding)

    # Step 6: Initialize wizard steps
    startup_logger.step("Setting up wizard steps", "🪄")
    with app.app_context():
        try:
            from .services.wizard_seed import import_default_wizard_steps

            import_default_wizard_steps()
            startup_logger.success("Wizard steps imported")
        except Exception as exc:
            # Non-fatal – log and continue startup to avoid blocking the app
            startup_logger.warning(f"Wizard step bootstrap failed: {exc}")

        # Step 7: Run wizard migrations
        startup_logger.step("Running wizard migrations", "🔄")
        try:
            from .services.wizard_migration import run_wizard_migrations

            migration_success = run_wizard_migrations()
            if migration_success:
                startup_logger.success("Wizard migrations completed")
            else:
                startup_logger.warning("Wizard step migrations had issues")
        except Exception as exc:
            # Non-fatal – log and continue startup to avoid blocking the app
            startup_logger.warning(f"Wizard step migration failed: {exc}")

    # Step 8: Startup complete
    startup_logger.step("Finalizing application setup", "✨")
    startup_logger.complete()

    return app
