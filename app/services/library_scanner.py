"""Library scanning service for media servers.

This service handles scanning and synchronizing library metadata from media servers
into the local database during application startup.
"""

import logging

logger = logging.getLogger(__name__)


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
    from app.services.media.service import get_client_for_media_server

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
            client = get_client_for_media_server(server)
            libraries_dict = client.libraries()  # {external_id: name}

            # Delete ALL old libraries for this server to avoid conflicts
            # This ensures a clean slate for the new external_id format
            old_count = Library.query.filter_by(server_id=server.id).count()
            Library.query.filter_by(server_id=server.id).delete()
            db.session.flush()

            # Insert fresh libraries with correct global IDs
            for external_id, name in libraries_dict.items():
                lib = Library(
                    external_id=external_id,
                    name=name,
                    server_id=server.id,
                    enabled=True,
                )
                db.session.add(lib)
                total_scanned += 1

            db.session.commit()

            if show_logs:
                logger.info(
                    f"Refreshed {len(libraries_dict)} libraries for {server.name} "
                    f"(removed {old_count} old entries)"
                )
        except Exception as server_exc:
            # Rollback on error to keep session clean
            db.session.rollback()
            error_msg = f"Failed to scan libraries for {server.name}: {server_exc}"
            errors.append(error_msg)
            if show_logs:
                logger.warning(error_msg)

    return total_scanned, errors
