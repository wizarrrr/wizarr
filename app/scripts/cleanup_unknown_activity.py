"""
Cleanup script for activity sessions with Unknown values.

This script provides options to handle legacy "Unknown" activity entries
that were created before the Tautulli-inspired enrichment fix.

Usage:
    from app.scripts.cleanup_unknown_activity import cleanup_unknown_activity

    # In Flask shell or script:
    cleanup_unknown_activity(app, mode='report')  # See what would be cleaned
    cleanup_unknown_activity(app, mode='delete')  # Actually delete them
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, cast

import structlog

from app.extensions import db
from app.models import ActivitySession


def cleanup_unknown_activity(
    app,
    mode: str = "report",
    min_age_days: int = 0,
    max_age_days: int | None = None,
) -> dict[str, Any]:
    """
    Clean up activity sessions with Unknown values.

    Args:
        app: Flask application instance
        mode: 'report' (dry run) or 'delete' (actually remove)
        min_age_days: Only process sessions older than this many days (default: 0 = all)
        max_age_days: Only process sessions younger than this many days (default: None = no limit)

    Returns:
        dict with statistics about the cleanup operation
    """
    logger = structlog.get_logger(__name__)

    with app.app_context():
        # Define what constitutes "Unknown"
        unknown_values = [
            "Unknown",
            "unknown",
            "Unknown User",
            "unknown user",
            "Unknown Device",
            "unknown device",
        ]

        # Build query for sessions with Unknown values
        query = db.session.query(ActivitySession).filter(
            db.or_(
                ActivitySession.user_name.in_(unknown_values),
                ActivitySession.media_title.in_(unknown_values),
                ActivitySession.device_name.in_(unknown_values),
            )
        )

        # Apply age filters
        now = datetime.now(UTC)
        if min_age_days > 0:
            cutoff_date = now - timedelta(days=min_age_days)
            query = query.filter(ActivitySession.started_at < cutoff_date)
            logger.info(f"Filtering sessions older than {min_age_days} days")

        if max_age_days is not None:
            recent_cutoff = now - timedelta(days=max_age_days)
            query = query.filter(ActivitySession.started_at >= recent_cutoff)
            logger.info(f"Filtering sessions younger than {max_age_days} days")

        # Get all matching sessions
        unknown_sessions = query.all()

        # Collect statistics
        stats = {
            "total_unknown": len(unknown_sessions),
            "by_field": {
                "unknown_user": 0,
                "unknown_title": 0,
                "unknown_device": 0,
            },
            "by_duration": {
                "very_short": 0,  # < 30s
                "short": 0,  # 30s - 5min
                "medium": 0,  # 5min - 30min
                "long": 0,  # > 30min
            },
            "by_status": {
                "active": 0,
                "inactive": 0,
            },
            "date_range": {
                "oldest": None,
                "newest": None,
            },
        }

        for session in unknown_sessions:
            # Count by field
            if session.user_name in unknown_values:
                stats["by_field"]["unknown_user"] += 1  # type: ignore
            if session.media_title in unknown_values:
                stats["by_field"]["unknown_title"] += 1  # type: ignore
            if session.device_name in unknown_values:
                stats["by_field"]["unknown_device"] += 1  # type: ignore

            # Count by duration
            duration_seconds = session.duration_ms / 1000 if session.duration_ms else 0
            if duration_seconds < 30:
                stats["by_duration"]["very_short"] += 1  # type: ignore
            elif duration_seconds < 300:  # 5 minutes
                stats["by_duration"]["short"] += 1  # type: ignore
            elif duration_seconds < 1800:  # 30 minutes
                stats["by_duration"]["medium"] += 1  # type: ignore
            else:
                stats["by_duration"]["long"] += 1  # type: ignore

            # Count by status
            if session.active:
                stats["by_status"]["active"] += 1  # type: ignore
            else:
                stats["by_status"]["inactive"] += 1  # type: ignore

            # Track date range
            date_range = cast(dict[str, Any], stats["date_range"])
            if (
                date_range["oldest"] is None
                or session.started_at < date_range["oldest"]
            ):
                date_range["oldest"] = session.started_at

            if (
                date_range["newest"] is None
                or session.started_at > date_range["newest"]
            ):
                date_range["newest"] = session.started_at

        # Log report
        logger.info("=" * 70)
        logger.info(f"Unknown Activity Cleanup Report - Mode: {mode.upper()}")
        logger.info("=" * 70)
        logger.info(f"Total sessions with Unknown values: {stats['total_unknown']}")
        logger.info("")
        logger.info("Breakdown by field:")
        by_field = cast(dict[str, int], stats["by_field"])
        logger.info(f"  - Unknown user:   {by_field['unknown_user']}")
        logger.info(f"  - Unknown title:  {by_field['unknown_title']}")
        logger.info(f"  - Unknown device: {by_field['unknown_device']}")
        logger.info("")
        logger.info("Breakdown by duration:")
        by_duration = cast(dict[str, int], stats["by_duration"])
        logger.info(f"  - Very short (<30s):    {by_duration['very_short']}")
        logger.info(f"  - Short (30s-5min):     {by_duration['short']}")
        logger.info(f"  - Medium (5min-30min):  {by_duration['medium']}")
        logger.info(f"  - Long (>30min):        {by_duration['long']}")
        logger.info("")
        logger.info("Breakdown by status:")
        by_status = cast(dict[str, int], stats["by_status"])
        logger.info(f"  - Active:   {by_status['active']}")
        logger.info(f"  - Inactive: {by_status['inactive']}")
        logger.info("")

        date_range = cast(dict[str, Any], stats["date_range"])
        if date_range["oldest"]:
            logger.info("Date range:")
            logger.info(f"  - Oldest: {date_range['oldest']}")
            logger.info(f"  - Newest: {date_range['newest']}")
            logger.info("")

        # Perform deletion if requested
        if mode == "delete":
            total_unknown = cast(int, stats["total_unknown"])
            if total_unknown > 0:
                logger.warning(
                    f"🗑️  DELETING {stats['total_unknown']} sessions with Unknown values..."
                )

                # Delete in batches to avoid locking issues
                batch_size = 100
                deleted_count = 0

                for i in range(0, len(unknown_sessions), batch_size):
                    batch = unknown_sessions[i : i + batch_size]
                    for session in batch:
                        db.session.delete(session)

                    db.session.commit()
                    deleted_count += len(batch)
                    logger.info(
                        f"Deleted batch: {deleted_count}/{stats['total_unknown']}"
                    )

                logger.info(f"✅ Successfully deleted {deleted_count} Unknown sessions")
                stats["deleted"] = deleted_count
            else:
                logger.info("✅ No Unknown sessions to delete")
                stats["deleted"] = 0

        elif mode == "report":
            logger.info("📋 This is a DRY RUN - no sessions were deleted")
            logger.info("   To actually delete these sessions, run with mode='delete'")
            stats["deleted"] = 0

        else:
            raise ValueError(f"Invalid mode: {mode}. Must be 'report' or 'delete'")

        logger.info("=" * 70)

        return stats
