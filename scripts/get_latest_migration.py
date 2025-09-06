#!/usr/bin/env python3
"""
Get the latest migration revision ID.
This is useful for release mappings and deployment scripts.
"""

import subprocess
import sys
from pathlib import Path


def get_latest_migration_from_alembic() -> str:
    """Get the current HEAD revision from alembic."""
    try:
        # Run flask db heads command
        result = subprocess.run(
            ["uv", "run", "flask", "db", "heads"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )

        if result.returncode != 0:
            raise RuntimeError(f"Alembic command failed: {result.stderr}")

        # Extract the revision ID from output
        output = result.stdout.strip()
        if output:
            # Handle format like "6c39692d6f32 (head)" or just "6c39692d6f32"
            return output.split()[0]
        raise RuntimeError("No HEAD revision found")

    except Exception as e:
        print(f"Error getting latest migration: {e}", file=sys.stderr)
        return ""


def main():
    """Main entry point."""
    if len(sys.argv) > 1 and sys.argv[1] in ("-h", "--help"):
        print("Usage: python get_latest_migration.py")
        print("Returns the current HEAD migration revision ID")
        return

    revision = get_latest_migration_from_alembic()
    if revision:
        print(revision)
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
