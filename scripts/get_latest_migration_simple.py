#!/usr/bin/env python3
"""
Get the latest migration revision ID by parsing migration files.
This avoids the Flask startup overhead.
"""

import re
import sys
from pathlib import Path


def parse_migration_file(file_path: Path) -> dict[str, str | None] | None:
    """Parse a migration file to extract revision info."""
    try:
        content = file_path.read_text()

        # Extract revision info from the file
        revision_match = re.search(r'revision\s*=\s*[\'"]([^\'"]+)[\'"]', content)
        down_revision_match = re.search(
            r'down_revision\s*=\s*[\'"]([^\'"]*)[\'"]', content
        )

        if not revision_match:
            return None

        return {
            "revision": revision_match.group(1),
            "down_revision": down_revision_match.group(1)
            if down_revision_match and down_revision_match.group(1) != "None"
            else None,
            "file": file_path.name,
        }
    except Exception:
        return None


def find_head_revision(migrations_dir: Path) -> str | None:
    """Find the HEAD revision by analyzing the migration chain."""
    migration_files = list(migrations_dir.glob("*.py"))

    migrations = []
    for file_path in migration_files:
        migration_data = parse_migration_file(file_path)
        if migration_data:
            migrations.append(migration_data)

    if not migrations:
        return None

    # Find revisions that are not referenced as down_revision by any other migration
    all_revisions = {m["revision"] for m in migrations}
    down_revisions = {m["down_revision"] for m in migrations if m["down_revision"]}

    heads = all_revisions - down_revisions

    if len(heads) == 1:
        return list(heads)[0]
    if len(heads) == 0:
        # Circular dependency or other issue
        return None
    # Multiple heads - return them all, let caller decide
    return ", ".join(sorted(heads))


def main():
    """Main entry point."""
    if len(sys.argv) > 1 and sys.argv[1] in ("-h", "--help"):
        print("Usage: python get_latest_migration_simple.py")
        print("Returns the current HEAD migration revision ID(s)")
        return

    migrations_dir = Path(__file__).parent.parent / "migrations" / "versions"

    if not migrations_dir.exists():
        print(
            f"Error: Migration directory not found: {migrations_dir}", file=sys.stderr
        )
        sys.exit(1)

    head_revision = find_head_revision(migrations_dir)
    if head_revision:
        print(head_revision)
        sys.exit(0)
    else:
        print("Error: Could not determine HEAD revision", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
