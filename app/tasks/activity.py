"""
Background tasks for activity monitoring.

Provides scheduled tasks for activity data maintenance, cleanup,
and monitoring health checks.
"""

try:
    from flask import Flask
except ImportError:  # pragma: no cover
    Flask = None  # type: ignore

import structlog
from structlog import get_logger as _get_logger

from app.services.activity import ActivityService


def cleanup_old_activity_task(app: Flask, retention_days: int = 90):
    """
    Cleanup old activity data beyond retention period.

    This task should be scheduled to run daily to manage database size.

    Args:
        app: Flask application instance
        retention_days: Number of days to retain activity data
    """
    logger = structlog.get_logger(__name__)

    try:
        with app.app_context():
            activity_service = ActivityService()
            deleted_count = activity_service.cleanup_old_activity(retention_days)

            logger.info(
                f"Activity cleanup completed: {deleted_count} old sessions removed"
            )
            return deleted_count

    except Exception as e:
        logger.error(f"Failed to cleanup old activity data: {e}", exc_info=True)
        return 0


def end_stale_sessions_task(app: Flask, timeout_hours: int = 24):
    """
    End sessions that have been active too long without updates.

    This task should be scheduled to run every few hours to clean up
    sessions that may have been left open due to client disconnections.

    Args:
        app: Flask application instance
        timeout_hours: Hours after which to consider a session stale
    """
    logger = structlog.get_logger(__name__)

    try:
        with app.app_context():
            activity_service = ActivityService()
            ended_count = activity_service.end_stale_sessions(timeout_hours)

            logger.info(
                f"Stale session cleanup completed: {ended_count} sessions ended"
            )
            return ended_count

    except Exception as e:
        logger.error(f"Failed to end stale sessions: {e}", exc_info=True)
        return 0


def monitor_health_check_task(app: Flask):
    """
    Check the health of activity monitoring connections.

    This task monitors WebSocket connections and logs any issues
    for debugging purposes.

    Args:
        app: Flask application instance
    """
    logger = structlog.get_logger(__name__)

    try:
        with app.app_context():
            # Get activity monitor from app extensions
            monitor = app.extensions.get("activity_monitor")

            if not monitor:
                logger.warning("Activity monitor not found in app extensions")
                return {"status": "no_monitor"}

            # Get connection status
            connection_status = monitor.get_connection_status()

            # Check for issues
            issues = []
            total_connections = len(connection_status)
            connected_count = 0
            total_errors = 0

            for server_id, status in connection_status.items():
                if status.get("connected", False):
                    connected_count += 1
                else:
                    issues.append(f"Server {server_id} disconnected")

                error_count = status.get("errors", 0)
                total_errors += error_count

                if error_count > 10:  # Threshold for concerning error count
                    issues.append(f"Server {server_id} has {error_count} errors")

            # Log health status
            health_status = {
                "total_connections": total_connections,
                "connected_count": connected_count,
                "total_errors": total_errors,
                "connection_rate": connected_count / total_connections
                if total_connections > 0
                else 0,
                "issues": issues,
            }

            if issues:
                logger.warning(f"Activity monitoring health issues detected: {issues}")
            else:
                logger.debug(
                    f"Activity monitoring health check passed: {connected_count}/{total_connections} connections active"
                )

            return health_status

    except Exception as e:
        logger.error(f"Failed to perform health check: {e}", exc_info=True)
        return {"status": "error", "error": str(e)}


def activity_monitoring_heartbeat_task(app: Flask):
    """
    Simple heartbeat task to ensure activity monitoring is running.

    This task can be used to restart monitoring if it has stopped
    unexpectedly.

    Args:
        app: Flask application instance
    """
    logger = structlog.get_logger(__name__)

    try:
        with app.app_context():
            monitor = app.extensions.get("activity_monitor")

            if not monitor:
                logger.warning("Activity monitor not available for heartbeat check")
                return False

            if not monitor.monitoring:
                logger.warning(
                    "Activity monitoring is not running, attempting to restart"
                )
                try:
                    monitor.start_monitoring()
                    logger.info("Activity monitoring restarted successfully")
                    return True
                except Exception as e:
                    logger.error(f"Failed to restart activity monitoring: {e}")
                    return False

            logger.debug("Activity monitoring heartbeat: OK")
            return True

    except Exception as e:
        logger.error(f"Failed to perform heartbeat check: {e}", exc_info=True)
        return False


def recover_sessions_on_startup_task(app: Flask):
    """
    Recover active sessions on startup by validating them against media servers.

    This task should be run once when Wizarr starts up to handle sessions
    that were active when the application last shut down.

    Args:
        app: Flask application instance
    """
    logger = structlog.get_logger(__name__)

    try:
        with app.app_context():
            activity_service = ActivityService()
            ended_count = activity_service.recover_sessions_on_startup()

            logger.info(
                f"Session recovery completed: {ended_count} orphaned sessions cleaned up"
            )
            return ended_count

    except Exception as e:
        logger.error(f"Failed to recover sessions on startup: {e}", exc_info=True)
        return 0


def get_activity_cleanup_interval() -> int:
    """Get the interval for activity cleanup task in hours."""
    # Run daily
    return 24


def get_stale_session_cleanup_interval() -> int:
    """Get the interval for stale session cleanup task in hours."""
    # Run every 6 hours
    return 6


def get_health_check_interval() -> int:
    """Get the interval for health check task in minutes."""
    # Run every 15 minutes
    return 15


def get_heartbeat_interval() -> int:
    """Get the interval for heartbeat task in minutes."""
    # Run every 5 minutes
    return 5


def register_activity_tasks(app: Flask, scheduler):
    """
    Register all activity monitoring tasks with the scheduler.

    Args:
        app: Flask application instance
        scheduler: APScheduler instance
    """
    logger = _get_logger()

    try:
        # Daily cleanup of old activity data
        scheduler.add_job(
            id="activity_cleanup",
            func=lambda: cleanup_old_activity_task(app),
            trigger="interval",
            hours=get_activity_cleanup_interval(),
            replace_existing=True,
            max_instances=1,
        )

        # Regular cleanup of stale sessions
        scheduler.add_job(
            id="activity_stale_cleanup",
            func=lambda: end_stale_sessions_task(app),
            trigger="interval",
            hours=get_stale_session_cleanup_interval(),
            replace_existing=True,
            max_instances=1,
        )

        # Health monitoring
        scheduler.add_job(
            id="activity_health_check",
            func=lambda: monitor_health_check_task(app),
            trigger="interval",
            minutes=get_health_check_interval(),
            replace_existing=True,
            max_instances=1,
        )

        # Heartbeat monitoring
        scheduler.add_job(
            id="activity_heartbeat",
            func=lambda: activity_monitoring_heartbeat_task(app),
            trigger="interval",
            minutes=get_heartbeat_interval(),
            replace_existing=True,
            max_instances=1,
        )

        logger.info("Activity monitoring tasks registered successfully")

    except Exception as e:
        logger.error(f"Failed to register activity tasks: {e}", exc_info=True)
