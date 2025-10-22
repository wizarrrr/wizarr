#!/usr/bin/env python3
"""
Standalone script to cleanup Unknown activity sessions.

This script can be run directly from the command line to clean up
legacy "Unknown" activity entries.

Usage:
    # Dry run - see what would be deleted
    python scripts/cleanup_unknown_sessions.py

    # Actually delete Unknown sessions
    python scripts/cleanup_unknown_sessions.py --delete

    # Delete only sessions older than 7 days
    python scripts/cleanup_unknown_sessions.py --delete --min-age-days 7

    # Delete sessions between 7 and 30 days old
    python scripts/cleanup_unknown_sessions.py --delete --min-age-days 7 --max-age-days 30
"""

import argparse
import sys
from pathlib import Path

# Add parent directory to path so we can import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import create_app
from app.scripts.cleanup_unknown_activity import cleanup_unknown_activity


def main():
    parser = argparse.ArgumentParser(
        description="Clean up activity sessions with Unknown values",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Report only (dry run)
  python scripts/cleanup_unknown_sessions.py

  # Actually delete Unknown sessions
  python scripts/cleanup_unknown_sessions.py --delete

  # Delete only sessions older than 7 days
  python scripts/cleanup_unknown_sessions.py --delete --min-age-days 7

  # Report on very old sessions (>90 days)
  python scripts/cleanup_unknown_sessions.py --min-age-days 90
        """,
    )

    parser.add_argument(
        "--delete",
        action="store_true",
        help="Actually delete the sessions (default is dry run)",
    )

    parser.add_argument(
        "--min-age-days",
        type=int,
        default=0,
        help="Only process sessions older than N days (default: 0)",
    )

    parser.add_argument(
        "--max-age-days",
        type=int,
        default=None,
        help="Only process sessions younger than N days (default: no limit)",
    )

    args = parser.parse_args()

    # Determine mode
    mode = "delete" if args.delete else "report"

    # Create Flask app
    print("🚀 Initializing Wizarr application...")
    app = create_app()

    # Run cleanup
    print(f"\n📊 Running cleanup in {mode.upper()} mode...\n")

    stats = cleanup_unknown_activity(
        app,
        mode=mode,
        min_age_days=args.min_age_days,
        max_age_days=args.max_age_days,
    )

    # Print summary
    print(f"\n{'=' * 70}")
    print("✅ Cleanup complete!")
    print(f"   Total Unknown sessions found: {stats['total_unknown']}")

    if mode == "delete":
        print(f"   Deleted: {stats.get('deleted', 0)}")
    else:
        print("\n💡 This was a DRY RUN - no sessions were deleted.")
        print("   To actually delete these sessions, add the --delete flag")

    print(f"{'=' * 70}\n")


if __name__ == "__main__":
    main()
