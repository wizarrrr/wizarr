import os

from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix

from .config import DevelopmentConfig
from .error_handlers import register_error_handlers
from .extensions import init_extensions
from .logging_config import configure_logging
from .middleware import require_onboarding


def create_app(config_object=DevelopmentConfig):
    """Create and configure Flask application with clean startup sequence."""
    from .logging_helpers import AppLogger, should_show_startup

    # Initialize logger and determine if we should show startup
    show_startup = should_show_startup()
    logger = AppLogger("wizarr.app")

    if show_startup:
        logger.welcome(os.getenv("APP_VERSION", "dev"))
        logger.start_sequence(total_steps=10)

    # Step 1: Configure logging
    if show_startup:
        logger.step("Configuring logging system", "📝")
    configure_logging()

    # Step 2: Create Flask application
    if show_startup:
        logger.step("Creating Flask application", "🌐")
    app = Flask(__name__)
    app.config.from_object(config_object)

    # Audit trail of changes to people's accounts (the wizarr.audit logger)
    from app.services import audit

    audit.register()

    # Apply ProxyFix if configured
    if app.config.get("TRUST_PROXY_HEADERS"):
        app.wsgi_app = ProxyFix(
            app.wsgi_app,
            x_for=app.config.get("PROXY_FIX_X_FOR", 1),
            x_proto=app.config.get("PROXY_FIX_X_PROTO", 1),
            x_host=app.config.get("PROXY_FIX_X_HOST", 1),
            x_port=app.config.get("PROXY_FIX_X_PORT", 1),
            x_prefix=app.config.get("PROXY_FIX_X_PREFIX", 1),
        )

    # Step 3: Initialize extensions
    if show_startup:
        logger.step("Initializing extensions", "🔧")
    init_extensions(app)

    # Step 4: Register blueprints
    if show_startup:
        logger.step("Registering blueprints", "🛡️")
    from .blueprints import all_blueprints

    for bp in all_blueprints:
        app.register_blueprint(bp)

    # Step 5: Setup context processors and filters
    if show_startup:
        logger.step("Configuring request processing", "⚙️")
    from .context_processors import (
        inject_app_version,
        inject_plus_features,
        inject_server_name,
    )

    app.context_processor(inject_server_name)
    app.context_processor(inject_plus_features)
    app.context_processor(inject_app_version)
    register_error_handlers(app)

    # Versioned static URLs, static cache headers and static compression
    from .static_assets import init_static_assets

    init_static_assets(app)

    # Register custom Jinja filters
    from .jinja_filters import register_filters

    register_filters(app)
    app.before_request(require_onboarding)

    # Step 6: Initialize wizard steps
    if show_startup:
        logger.step("Setting up wizard steps", "🪄")
    from .background import startup_data_lock

    # With more than one gunicorn worker, each worker creates the app at the
    # same time. The lock makes the workers do steps 6 and 7 one at a time.
    with app.app_context(), startup_data_lock():
        try:
            from .services.wizard_seed import import_default_wizard_steps

            import_default_wizard_steps()
            if show_startup:
                logger.success("Wizard steps imported")
        except Exception as exc:
            # Non-fatal – log and continue startup to avoid blocking the app
            logger.warning(f"Wizard step bootstrap failed: {exc}")

        # Step 7: Run wizard migrations
        if show_startup:
            logger.step("Running wizard migrations", "🔄")
        try:
            from .services.wizard_migration import run_wizard_migrations

            migration_success = run_wizard_migrations()
            if show_startup:
                if migration_success:
                    logger.success("Wizard migrations completed")
                else:
                    logger.warning("Wizard step migrations had issues")
        except Exception as exc:
            # Non-fatal – log and continue startup to avoid blocking the app
            logger.warning(f"Wizard step migration failed: {exc}")

    # Step 8: Initialize Plus features if enabled
    if show_startup:
        logger.step("Checking for Plus features", "⭐")

    # Check if plus features should be enabled
    plus_enabled = os.getenv("WIZARR_PLUS_ENABLED", "false").lower() in (
        "true",
        "1",
        "yes",
    )

    if plus_enabled:
        try:
            import plus

            plus.enable_plus_features()  # type: ignore

            with app.app_context():
                plus.initialize_plus_features(app)  # type: ignore

            if show_startup:
                logger.success("Plus features enabled")
        except ImportError:
            if show_startup:
                logger.warning("Plus features requested but plus module not found")
        except Exception as exc:
            if show_startup:
                logger.warning(f"Plus features initialization failed: {exc}")
    elif show_startup:
        logger.info("Plus features disabled")

    # Step 9: Start background services. Only one process (the background
    # leader) runs the scheduler, the activity monitor, the startup
    # migrations and the startup tasks. The library scan and the manifest
    # fetch run in the background, so they do not delay startup.
    if show_startup:
        logger.step("Starting background services", "🕒")
    from .background import start_background_services

    role = start_background_services(app)
    if show_startup:
        if role == "leader":
            logger.success(f"Background leader (pid {os.getpid()})")
        elif role == "standby":
            logger.info("Another process runs the background services")
        else:
            logger.info("Background services skipped in this process")

    # Step 10: Show scheduler status and complete startup
    if show_startup:
        logger.step("Finalizing application setup", "✨")

        # Show scheduler status right in the main startup sequence
        from .extensions import scheduler

        if scheduler and hasattr(scheduler, "scheduler") and scheduler.scheduler:
            if scheduler.running:
                dev_mode = os.getenv("WIZARR_ENABLE_SCHEDULER", "false").lower() in (
                    "true",
                    "1",
                    "yes",
                )
                logger.scheduler_status(enabled=True, dev_mode=dev_mode)
            else:
                logger.info("Scheduler not running in this process")
        else:
            logger.info("Scheduler disabled")

        # Complete startup sequence
        logger.complete()

    return app
