import os

from flask import Flask

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

    # Initialise activity monitoring (blueprint already registered above)
    from app.activity import init_app as init_activity

    init_activity(app)

    # Register activity scheduler tasks if the scheduler is available
    try:
        from .extensions import scheduler as activity_scheduler

        if (
            activity_scheduler
            and hasattr(activity_scheduler, "scheduler")
            and activity_scheduler.scheduler
        ):
            from app.tasks.activity import register_activity_tasks

            register_activity_tasks(app, activity_scheduler)
    except Exception as exc:
        app.logger.warning(f"Failed to register activity tasks: {exc}")

    # Step 5: Setup context processors and filters
    if show_startup:
        logger.step("Configuring request processing", "⚙️")
    from .context_processors import inject_plus_features, inject_server_name

    app.context_processor(inject_server_name)
    app.context_processor(inject_plus_features)
    register_error_handlers(app)

    # Register custom Jinja filters
    from .jinja_filters import register_filters

    register_filters(app)
    app.before_request(require_onboarding)

    # Step 6: Initialize wizard steps
    if show_startup:
        logger.step("Setting up wizard steps", "🪄")
    with app.app_context():
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

        # Step 8: Scan libraries for all media servers
        if show_startup:
            logger.step("Scanning media server libraries", "📚")
        try:
            from .services.library_scanner import scan_all_server_libraries

            total_scanned, _ = scan_all_server_libraries(show_logs=show_startup)

            if show_startup:
                if total_scanned > 0:
                    logger.success(f"Scanned {total_scanned} libraries")
                else:
                    logger.info("No media servers configured")
        except Exception as exc:
            # Non-fatal – log and continue startup to avoid blocking the app
            if show_startup:
                logger.warning(f"Library scanning failed: {exc}")

    # Step 9: Initialize Plus features if enabled
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

            plus.enable_plus_features()

            with app.app_context():
                plus.initialize_plus_features(app)

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
                logger.info("Scheduler initialized but not running")
        else:
            logger.info("Scheduler disabled")

        # Complete startup sequence
        logger.complete()

    return app
