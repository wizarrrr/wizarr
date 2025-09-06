#!/usr/bin/env python3
r"""
Pre-commit hook to enforce migration naming conventions.
Add this to .pre-commit-config.yaml:

  - repo: local
    hooks:
      - id: check-migration-naming
        name: Check migration naming convention
        entry: python scripts/check_migration_naming.py
        language: system
        files: ^migrations/versions/.*\.py$
"""

import re
import sys
from datetime import datetime
from pathlib import Path


def check_migration_naming(file_path: Path) -> tuple[bool, str]:
    """Check if migration follows naming convention."""
    filename = file_path.name

    # Preferred format: YYYYMMDD_description.py or YYYYMMDD_HH_description.py
    date_pattern = r"^(\d{8})(?:_\d{2})?_([a-zA-Z0-9_]+)\.py$"

    # Legacy acceptable formats (don't enforce for existing files)
    hash_pattern = r"^[a-f0-9]{12}_([a-zA-Z0-9_]+)\.py$"
    squashed_pattern = r"^.*squashed.*\.py$"

    if re.match(date_pattern, filename):
        # Check if date is valid
        date_part = filename[:8]
        try:
            datetime.strptime(date_part, "%Y%m%d")
            return True, "✅ Good naming convention (date-based)"
        except ValueError:
            return False, f"❌ Invalid date in filename: {date_part}"

    elif re.match(hash_pattern, filename):
        return True, "⚠️  Legacy hash-based naming (acceptable for existing files)"

    elif re.match(squashed_pattern, filename, re.IGNORECASE):
        return True, "ℹ️  Squashed migration (acceptable)"

    elif filename.endswith("_.py"):
        return False, "❌ Empty description - provide meaningful migration name"

    else:
        return False, "❌ Invalid naming convention. Use: YYYYMMDD_description.py"


def check_migration_content(file_path: Path) -> tuple[bool, list[str]]:
    """Check migration file content for best practices."""
    issues = []

    try:
        content = file_path.read_text()

        # Check for revision ID
        if not re.search(r'revision\s*=\s*[\'"]([^\'"]+)[\'"]', content):
            issues.append("Missing revision ID")

        # Check for down_revision
        if not re.search(r"down_revision\s*=", content):
            issues.append("Missing down_revision")

        # Check for docstring
        if '"""' not in content and "'''" not in content:
            issues.append(
                "Missing docstring - add description of what this migration does"
            )

        # Check for upgrade/downgrade functions
        if "def upgrade():" not in content:
            issues.append("Missing upgrade() function")

        if "def downgrade():" not in content:
            issues.append("Missing downgrade() function")

    except Exception as e:
        issues.append(f"Could not read file: {e}")

    return len(issues) == 0, issues


def main():
    """Main entry point for pre-commit hook."""
    if len(sys.argv) < 2:
        print("Usage: python check_migration_naming.py <migration_files...>")
        sys.exit(1)

    migration_files = [Path(f) for f in sys.argv[1:]]
    all_passed = True

    print("🔍 Checking migration naming conventions...")

    for file_path in migration_files:
        if not file_path.exists():
            print(f"❌ File not found: {file_path}")
            all_passed = False
            continue

        # Check naming
        naming_ok, naming_msg = check_migration_naming(file_path)

        # Check content
        content_ok, content_issues = check_migration_content(file_path)

        # Report results
        print(f"\n📄 {file_path.name}:")
        print(f"   Naming: {naming_msg}")

        if not content_ok:
            print("   Content issues:")
            for issue in content_issues:
                print(f"      • {issue}")
        else:
            print("   Content: ✅ Looks good")

        if not naming_ok or not content_ok:
            all_passed = False

    if not all_passed:
        print("\n💡 Migration Naming Guidelines:")
        print("   • Use date-based naming: YYYYMMDD_description.py")
        print("   • Provide meaningful descriptions (no empty descriptions)")
        print("   • Include proper docstrings explaining what the migration does")
        print("   • Ensure upgrade() and downgrade() functions exist")
        sys.exit(1)
    else:
        print("\n✅ All migrations follow naming conventions!")
        sys.exit(0)


if __name__ == "__main__":
    main()
