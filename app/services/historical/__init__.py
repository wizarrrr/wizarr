"""
Historical data import service for Wizarr.

This service handles importing historical viewing data from media servers
into the ActivitySession model for unified analytics.
"""

import threading
from datetime import UTC, datetime
from typing import Any

import structlog
from flask import current_app

from app.models import ActivitySession, HistoricalImportJob, MediaServer, db
from app.services.historical.importers import (
    AudiobookShelfHistoricalImporter,
    JellyfinHistoricalImporter,
    PlexHistoricalImporter,
)

logger = structlog.get_logger(__name__)


class HistoricalDataService:
    """Service for importing and managing historical viewing data."""

    def __init__(self, server_id: int):
        self.server_id = server_id
        self.media_server = MediaServer.query.get(server_id)
        if not self.media_server:
            raise ValueError(f"Media server {server_id} not found")

    def start_async_import(self, days_back: int, max_results: int | None = None):
        """Launch a background job to import historical data."""
        job = HistoricalImportJob(
            server_id=self.server_id,
            days_back=days_back,
            max_results=max_results,
            status=HistoricalImportJob.STATUS_QUEUED,
        )
        db.session.add(job)
        db.session.commit()

        app = current_app._get_current_object()  # type: ignore[attr-defined]

        worker = threading.Thread(
            target=self._run_import_job,
            args=(app, job.id, self.server_id, days_back, max_results),
            name=f"historical-import-{job.id}",
            daemon=True,
        )
        worker.start()

        return job

    def import_history(
        self,
        days_back: int = 30,
        max_results: int | None = 1000,
        job_id: int | None = None,
    ) -> dict[str, Any]:
        """Dispatch historical import based on server type."""
        server_type = (self.media_server.server_type or "").lower()

        if server_type == "plex":
            return self._import_plex_history(
                days_back=days_back, max_results=max_results, job_id=job_id
            )
        if server_type in {"jellyfin", "emby"}:
            return self._import_jellyfin_history(
                days_back=days_back, max_results=max_results, job_id=job_id
            )
        if server_type == "audiobookshelf":
            return self._import_audiobookshelf_history(
                days_back=days_back, max_results=max_results, job_id=job_id
            )

        raise ValueError(f"Historical import not supported for {server_type!r}")

    def import_plex_history(
        self,
        days_back: int = 30,
        max_results: int | None = 1000,
        job_id: int | None = None,
    ) -> dict[str, Any]:
        """Backward-compatible Plex history import entry point."""
        return self._import_plex_history(
            days_back=days_back, max_results=max_results, job_id=job_id
        )

    def _import_plex_history(
        self,
        days_back: int,
        max_results: int | None,
        job_id: int | None,
    ) -> dict[str, Any]:
        """Import historical viewing data from Plex."""
        importer = PlexHistoricalImporter(self.server_id, self.media_server)
        result = importer.import_history(
            days_back, max_results, job_id, self._update_job
        )

        if result["success"]:
            stored_count = self._store_activity_sessions(
                result["sessions"], job_id=job_id
            )
            if job_id is not None:
                self._update_job(
                    job_id,
                    total_processed=result["total_processed"],
                    total_stored=stored_count,
                )
            return {
                **result,
                "total_stored": stored_count,
            }
        if job_id is not None:
            self._update_job(
                job_id,
                status=HistoricalImportJob.STATUS_FAILED,
                error_message=result["error"],
            )
        return {
            **result,
            "total_stored": 0,
        }

    def _import_jellyfin_history(
        self,
        days_back: int,
        max_results: int | None,
        job_id: int | None,
    ) -> dict[str, Any]:
        """Import historical playback data from Jellyfin/Emby."""
        importer = JellyfinHistoricalImporter(self.server_id, self.media_server)
        result = importer.import_history(
            days_back, max_results, job_id, self._update_job
        )

        stored_count = self._store_activity_sessions(result["sessions"], job_id=job_id)

        if job_id is not None:
            self._update_job(
                job_id,
                total_fetched=result["total_fetched"],
                total_processed=result["total_processed"],
                total_stored=stored_count,
            )

        return {
            **result,
            "total_stored": stored_count,
        }

    def _import_audiobookshelf_history(
        self,
        days_back: int,
        max_results: int | None,
        job_id: int | None,
    ) -> dict[str, Any]:
        """Import historical listening session data from AudiobookShelf."""
        importer = AudiobookShelfHistoricalImporter(self.server_id, self.media_server)
        result = importer.import_history(
            days_back, max_results, job_id, self._update_job
        )

        if not result["success"]:
            if job_id is not None:
                self._update_job(
                    job_id,
                    status=HistoricalImportJob.STATUS_FAILED,
                    error_message=result["error"],
                )
            return {
                **result,
                "total_stored": 0,
            }

        stored_count = self._store_activity_sessions(result["sessions"], job_id=job_id)

        if job_id is not None:
            self._update_job(
                job_id,
                total_fetched=result["total_fetched"],
                total_processed=result["total_processed"],
                total_stored=stored_count,
            )

        return {
            **result,
            "total_stored": stored_count,
        }

    def _store_activity_sessions(
        self, sessions: list, job_id: int | None = None
    ) -> int:
        """Store activity sessions in the database."""
        stored_count = 0

        for session in sessions:
            try:
                # Check if session already exists
                existing = (
                    ActivitySession.query.filter_by(
                        session_id=session.session_id, server_id=session.server_id
                    )
                    .with_entities(ActivitySession.id)
                    .first()
                )

                if existing:
                    continue

                db.session.add(session)
                db.session.commit()
                stored_count += 1

                if job_id is not None and stored_count % 25 == 0:
                    self._update_job(job_id, total_stored=stored_count)

            except Exception as exc:
                logger.warning(
                    "session_store_failed",
                    session_id=getattr(session, "session_id", "unknown"),
                    server_id=getattr(session, "server_id", "unknown"),
                    error=str(exc),
                )
                db.session.rollback()
                if job_id is not None:
                    self._update_job(job_id, error_message=str(exc))

        if job_id is not None:
            self._update_job(job_id, total_stored=stored_count)

        return stored_count

    @staticmethod
    def _update_job(job_id: int, **fields) -> None:
        """Persist updates to a historical import job."""
        job = HistoricalImportJob.query.get(job_id)
        if not job:
            return

        for key, value in fields.items():
            setattr(job, key, value)
        job.updated_at = datetime.now(UTC)
        db.session.commit()

    @staticmethod
    def _run_import_job(
        app,
        job_id: int,
        server_id: int,
        days_back: int,
        max_results: int | None,
    ) -> None:
        """Background worker wrapper for historical imports."""
        with app.app_context():
            job = HistoricalImportJob.query.get(job_id)
            if not job:
                logger.error("import_job_not_found", job_id=job_id)
                return

            job.status = HistoricalImportJob.STATUS_RUNNING
            job.started_at = datetime.now(UTC)
            job.error_message = None
            job.total_fetched = 0
            job.total_processed = 0
            job.total_stored = 0
            job.updated_at = datetime.now(UTC)
            db.session.commit()

            service = HistoricalDataService(server_id)

            try:
                result = service.import_history(
                    days_back=days_back,
                    max_results=max_results,
                    job_id=job_id,
                )
                job = HistoricalImportJob.query.get(job_id)
                if not job:
                    return
                if result.get("success"):
                    job.status = HistoricalImportJob.STATUS_COMPLETED
                else:
                    job.status = HistoricalImportJob.STATUS_FAILED
                    job.error_message = result.get("error")
                job.total_fetched = result.get("total_fetched", job.total_fetched)
                job.total_processed = result.get("total_processed", job.total_processed)
                job.total_stored = result.get("total_stored", job.total_stored)
                job.updated_at = datetime.now(UTC)
                db.session.commit()
            except Exception as exc:
                logger.error("import_job_failed", job_id=job_id, error=str(exc))
                db.session.rollback()
                job = HistoricalImportJob.query.get(job_id)
                if job:
                    job.status = HistoricalImportJob.STATUS_FAILED
                    job.error_message = str(exc)
                    job.updated_at = datetime.now(UTC)
                    db.session.commit()
            finally:
                job = HistoricalImportJob.query.get(job_id)
                if job:
                    job.finished_at = datetime.now(UTC)
                    job.updated_at = datetime.now(UTC)
                    db.session.commit()

            # Clean up completed jobs
            job = HistoricalImportJob.query.get(job_id)
            if job and job.status == HistoricalImportJob.STATUS_COMPLETED:
                db.session.delete(job)
                db.session.commit()

    def get_import_statistics(self) -> dict[str, Any]:
        """Get statistics about imported historical data."""
        try:
            # Get counts for imported historical data
            imported_query = ActivitySession.query.filter(
                ActivitySession.server_id == self.server_id,
                db.or_(
                    ActivitySession.session_metadata.like(
                        '%"imported_from": "plex_history"%'
                    ),
                    ActivitySession.session_metadata.like(
                        '%"imported_from": "jellyfin_history"%'
                    ),
                    ActivitySession.session_metadata.like(
                        '%"imported_from": "emby_history"%'
                    ),
                    ActivitySession.session_metadata.like(
                        '%"imported_from": "audiobookshelf_history"%'
                    ),
                ),
            )

            total_entries = imported_query.count()
            unique_users = (
                db.session.query(ActivitySession.user_id)
                .filter(
                    ActivitySession.server_id == self.server_id,
                    db.or_(
                        ActivitySession.session_metadata.like(
                            '%"imported_from": "plex_history"%'
                        ),
                        ActivitySession.session_metadata.like(
                            '%"imported_from": "jellyfin_history"%'
                        ),
                        ActivitySession.session_metadata.like(
                            '%"imported_from": "emby_history"%'
                        ),
                        ActivitySession.session_metadata.like(
                            '%"imported_from": "audiobookshelf_history"%'
                        ),
                    ),
                )
                .distinct()
                .count()
            )

            # Get date range
            oldest_entry = imported_query.order_by(
                ActivitySession.started_at.asc()
            ).first()
            newest_entry = imported_query.order_by(
                ActivitySession.started_at.desc()
            ).first()

            return {
                "total_entries": total_entries,
                "unique_users": unique_users,
                "date_range": {
                    "oldest": oldest_entry.started_at.isoformat()
                    if oldest_entry
                    else None,
                    "newest": newest_entry.started_at.isoformat()
                    if newest_entry
                    else None,
                },
            }

        except Exception as e:
            logger.error("statistics_fetch_failed", error=str(e))
            return {
                "total_entries": 0,
                "unique_users": 0,
                "date_range": {"oldest": None, "newest": None},
            }

    def clear_historical_data(self) -> dict[str, Any]:
        """Clear all imported historical data for this server."""
        try:
            # Delete only imported historical data
            deleted_count = ActivitySession.query.filter(
                ActivitySession.server_id == self.server_id,
                db.or_(
                    ActivitySession.session_metadata.like(
                        '%"imported_from": "plex_history"%'
                    ),
                    ActivitySession.session_metadata.like(
                        '%"imported_from": "jellyfin_history"%'
                    ),
                    ActivitySession.session_metadata.like(
                        '%"imported_from": "emby_history"%'
                    ),
                    ActivitySession.session_metadata.like(
                        '%"imported_from": "audiobookshelf_history"%'
                    ),
                ),
            ).count()

            ActivitySession.query.filter(
                ActivitySession.server_id == self.server_id,
                db.or_(
                    ActivitySession.session_metadata.like(
                        '%"imported_from": "plex_history"%'
                    ),
                    ActivitySession.session_metadata.like(
                        '%"imported_from": "jellyfin_history"%'
                    ),
                    ActivitySession.session_metadata.like(
                        '%"imported_from": "emby_history"%'
                    ),
                    ActivitySession.session_metadata.like(
                        '%"imported_from": "audiobookshelf_history"%'
                    ),
                ),
            ).delete(synchronize_session=False)

            db.session.commit()

            return {"success": True, "deleted_count": deleted_count}

        except Exception as e:
            logger.error("clear_data_failed", error=str(e))
            db.session.rollback()
            return {"success": False, "error": str(e), "deleted_count": 0}


__all__ = ["HistoricalDataService"]
