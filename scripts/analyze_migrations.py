#!/usr/bin/env python3
"""
Analyze migration files to understand the naming chaos and migration chain.
"""

import re
from pathlib import Path


def parse_migration_file(file_path: Path) -> dict[str, str | None]:
    """Parse a migration file to extract revision info."""
    content = file_path.read_text()

    # Extract revision info from the file
    revision_match = re.search(r'revision\s*=\s*[\'"]([^\'"]+)[\'"]', content)
    down_revision_match = re.search(r'down_revision\s*=\s*[\'"]([^\'"]*)[\'"]', content)
    branch_labels_match = re.search(r'branch_labels\s*=\s*[\'"]([^\'"]*)[\'"]', content)
    depends_on_match = re.search(r'depends_on\s*=\s*[\'"]([^\'"]*)[\'"]', content)

    return {
        "file": file_path.name,
        "revision": revision_match.group(1) if revision_match else None,
        "down_revision": down_revision_match.group(1) if down_revision_match else None,
        "branch_labels": branch_labels_match.group(1) if branch_labels_match else None,
        "depends_on": depends_on_match.group(1) if depends_on_match else None,
    }


def analyze_naming_patterns(files: list[Path]) -> dict[str, list[str]]:
    """Categorize files by their naming patterns."""
    patterns = {
        "date_based": [],  # 20250611_description.py
        "hash_only": [],  # abc123def456.py
        "hash_desc": [],  # abc123def456_description.py
        "squashed": [],  # contains 'squashed'
        "empty_desc": [],  # ends with _.py
        "other": [],
    }

    for file in files:
        name = file.name

        if "squashed" in name.lower():
            patterns["squashed"].append(name)
        elif re.match(r"^\d{8}_.*\.py$", name):
            patterns["date_based"].append(name)
        elif re.match(r"^[a-f0-9]{12}_.*\.py$", name):
            patterns["hash_desc"].append(name)
        elif re.match(r"^[a-f0-9]{12}\.py$", name):
            patterns["hash_only"].append(name)
        elif name.endswith("_.py"):
            patterns["empty_desc"].append(name)
        else:
            patterns["other"].append(name)

    return patterns


def find_migration_heads(migrations: list[dict]) -> list[str]:
    """Find migration heads (revisions that aren't down_revision of any other)."""
    all_revisions = {m["revision"] for m in migrations if m["revision"]}
    down_revisions = {
        m["down_revision"]
        for m in migrations
        if m["down_revision"] and m["down_revision"] != "None"
    }

    heads = all_revisions - down_revisions
    return list(heads)


def build_migration_chain(migrations: list[dict]) -> dict[str, str]:
    """Build a mapping of revision -> down_revision to understand the chain."""
    chain = {}
    for migration in migrations:
        if migration["revision"] and migration["down_revision"]:
            chain[migration["revision"]] = migration["down_revision"]
    return chain


def main():
    """Analyze the migrations directory."""
    migrations_dir = Path(__file__).parent.parent / "migrations" / "versions"

    if not migrations_dir.exists():
        print(f"❌ Migrations directory not found: {migrations_dir}")
        return

    # Get all migration files
    migration_files = list(migrations_dir.glob("*.py"))
    print(f"📊 Found {len(migration_files)} migration files")
    print()

    # Analyze naming patterns
    patterns = analyze_naming_patterns(migration_files)
    print("🏷️  NAMING PATTERNS:")
    for pattern, files in patterns.items():
        if files:
            print(f"   {pattern}: {len(files)} files")
            for f in files[:3]:  # Show first 3 examples
                print(f"      • {f}")
            if len(files) > 3:
                print(f"      ... and {len(files) - 3} more")
            print()

    # Parse migration files
    print("🔍 PARSING MIGRATION FILES...")
    migrations = []
    parse_errors = []

    for file_path in migration_files:
        try:
            migration_data = parse_migration_file(file_path)
            migrations.append(migration_data)
        except Exception as e:
            parse_errors.append(f"{file_path.name}: {e}")

    if parse_errors:
        print("⚠️  PARSE ERRORS:")
        for error in parse_errors:
            print(f"   • {error}")
        print()

    # Find heads
    heads = find_migration_heads(migrations)
    print(f"🎯 MIGRATION HEADS ({len(heads)}):")
    for head in heads:
        # Find the file for this revision
        for migration in migrations:
            if migration["revision"] == head:
                print(f"   • {head} ({migration['file']})")
                break
    print()

    # Build chain
    chain = build_migration_chain(migrations)
    print(f"🔗 MIGRATION CHAIN ({len(chain)} links):")

    # Show orphaned migrations (no down_revision)
    orphans = [
        m for m in migrations if not m["down_revision"] or m["down_revision"] == "None"
    ]
    if orphans:
        print(f"   🔸 Orphaned migrations ({len(orphans)}):")
        for orphan in orphans:
            print(f"      • {orphan['revision']} ({orphan['file']})")
        print()

    # Show potential issues
    print("⚠️  POTENTIAL ISSUES:")

    # Multiple heads
    if len(heads) > 1:
        print(f"   • Multiple heads detected ({len(heads)} heads)")
        print("     This can cause merge conflicts and branching issues")

    # Empty descriptions
    if patterns["empty_desc"]:
        print(f"   • {len(patterns['empty_desc'])} migrations with empty descriptions")
        print("     Makes it hard to understand what the migration does")

    # Mixed naming conventions
    non_empty_patterns = {k: v for k, v in patterns.items() if v}
    if len(non_empty_patterns) > 2:
        print(
            f"   • Mixed naming conventions ({len(non_empty_patterns)} different patterns)"
        )
        print("     Makes it hard to understand chronological order")

    print()
    print("💡 RECOMMENDATIONS:")
    print("   1. Use 'alembic merge' to consolidate multiple heads")
    print("   2. Standardize on date-based naming: YYYYMMDD_description")
    print("   3. Always provide meaningful descriptions")
    print("   4. Consider squashing very old migrations periodically")
    print("   5. Add a pre-commit hook to enforce naming conventions")


if __name__ == "__main__":
    main()
