"""Library scanning service for media servers.

This service handles scanning and synchronizing library metadata from media servers
into the local database during application startup.

Reconciliation itself is delegated to ``media.service.upsert_scanned_libraries``,
the same helper the invite modal and the server edit form use, so every scan path
treats ``Library.enabled`` (the admin's saved invite default) identically.
"""

import logging
from functools import partial

logger = logging.getLogger(__name__)

# Read timeout of each request of a library scan (in seconds).
LIBRARY_SCAN_TIMEOUT = 30

# Total time limit for the scan of all servers (in seconds). A Plex scan
# makes 3-4 calls one after the other (plex.tv sign-in, the plex.tv servers
# API, the server root and the library sections), so the limit must be larger
# than one read timeout. The startup scan runs in a background thread, so
# this limit does not delay startup.
LIBRARY_SCAN_DEADLINE = 60

# Short connect timeout, so that an offline host fails fast.
_LIBRARY_SCAN_CONNECT_TIMEOUT = 5


def scan_all_server_libraries(show_logs: bool = True) -> tuple[int, list[str]]:
    """Scan libraries for all configured media servers.

    The servers are scanned in parallel. The network calls run in worker
    threads. The DB writes run in the calling thread, one short transaction
    for each server. A server that does not answer in
    ``LIBRARY_SCAN_DEADLINE`` seconds is reported as an error.

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
    from app.services.media import service as media_service

    # Check if the library table exists (in case migrations haven't run yet)
    inspector = inspect(db.engine)
    if not inspector.has_table("library"):
        if show_logs:
            logger.info("Library table doesn't exist yet - skipping scan")
        raise Exception("Library table not found - run migrations first")

    servers = MediaServer.query.all()
    total_scanned = 0
    errors = []

    # Make the clients in this thread, from this thread's DB session.
    scan_jobs = []
    for server in servers:
        try:
            client = media_service.get_client_for_media_server(server)
        except Exception as server_exc:
            error_msg = f"Failed to scan libraries for {server.name}: {server_exc}"
            errors.append(error_msg)
            if show_logs:
                logger.warning(error_msg)
            continue
        client.timeout = (_LIBRARY_SCAN_CONNECT_TIMEOUT, LIBRARY_SCAN_TIMEOUT)
        scan_jobs.append((server, client))

    def _scan(client):
        scan_result = client.libraries()
        return scan_result, client.libraries_scan_authoritative(scan_result)

    results = media_service.run_parallel(
        [partial(_scan, client) for _server, client in scan_jobs],
        deadline=LIBRARY_SCAN_DEADLINE,
    )

    for (server, _client), (status, value) in zip(scan_jobs, results, strict=True):
        server_name = server.name
        try:
            if status == "timeout":
                raise TimeoutError(f"no answer within {LIBRARY_SCAN_DEADLINE} s")
            if status == "error":
                raise value

            scan_result, authoritative = value
            before = Library.query.filter_by(server_id=server.id).count()

            media_service.upsert_scanned_libraries(
                server, scan_result, authoritative=authoritative
            )
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
                    f"Refreshed {scanned} libraries for {server_name} "
                    f"(rows {before} -> {after}, authoritative={authoritative})"
                )
        except Exception as server_exc:
            # Rollback on error to keep session clean
            db.session.rollback()
            error_msg = f"Failed to scan libraries for {server_name}: {server_exc}"
            errors.append(error_msg)
            if show_logs:
                logger.warning(error_msg)

    return total_scanned, errors
