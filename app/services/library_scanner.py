"""Library scanning service for media servers.

This service handles scanning and synchronizing library metadata from media servers
into the local database during application startup.

Reconciliation itself is delegated to ``media.service.upsert_scanned_libraries``,
the same helper the invite modal and the server edit form use, so every scan path
treats ``Library.enabled`` (the admin's saved invite default) identically.
"""

import logging

logger = logging.getLogger(__name__)

# Timeout for individual server library scans (in seconds)
# This prevents a single unreachable server from blocking startup
LIBRARY_SCAN_TIMEOUT = 15


def scan_all_server_libraries(show_logs: bool = True) -> tuple[int, list[str]]:
    """Scan libraries for all configured media servers.

    Args:
        show_logs: Whether to output log messages during scanning

    Returns:
        Tuple of (total_scanned, error_messages)
        - total_scanned: Number of libraries successfully scanned
        - error_messages: List of error messages for failed scans
    """
    from sqlalchemy import inspect

    from app.extensions import db
    from app.models import Library, MediaServer
    from app.services.media.service import (
        scan_libraries_for_server,
        upsert_scanned_libraries,
    )

    # Check if the library table exists (in case migrations haven't run yet)
    inspector = inspect(db.engine)
    if not inspector.has_table("library"):
        if show_logs:
            logger.info("Library table doesn't exist yet - skipping scan")
        raise Exception("Library table not found - run migrations first")

    servers = MediaServer.query.all()
    total_scanned = 0
    errors = []

    for server in servers:
        try:
            before = Library.query.filter_by(server_id=server.id).count()

            scan_result, authoritative = scan_libraries_for_server(server)
            upsert_scanned_libraries(server, scan_result, authoritative=authoritative)
            db.session.commit()

            try:
                scanned = len(scan_result)
            except TypeError:
                # Malformed result; upsert_scanned_libraries already no-opped.
                scanned = 0
            total_scanned += scanned

            if show_logs:
                after = Library.query.filter_by(server_id=server.id).count()
                logger.info(
                    f"Refreshed {scanned} libraries for {server.name} "
                    f"(rows {before} -> {after}, authoritative={authoritative})"
                )
        except Exception as server_exc:
            # Rollback on error to keep session clean
            db.session.rollback()
            error_msg = f"Failed to scan libraries for {server.name}: {server_exc}"
            errors.append(error_msg)
            if show_logs:
                logger.warning(error_msg)

    return total_scanned, errors
