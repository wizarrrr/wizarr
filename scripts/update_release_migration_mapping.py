#!/usr/bin/env python3
"""
Helper script to update release migration mappings automatically.
Run this when preparing a release to update the test mappings.
"""

import re
import sys
from pathlib import Path


def get_current_head() -> str:
    """Get current HEAD migration using the simple script."""
    script_path = Path(__file__).parent / "get_latest_migration_simple.py"

    import subprocess

    result = subprocess.run(
        [sys.executable, str(script_path)], capture_output=True, text=True
    )

    if result.returncode == 0:
        return result.stdout.strip()
    raise RuntimeError(f"Could not get HEAD migration: {result.stderr}")


def update_test_file(release_version: str, head_revision: str):
    """Update the test file with the new release mapping."""
    test_file = Path(__file__).parent.parent / "tests" / "test_migrations.py"

    if not test_file.exists():
        raise FileNotFoundError(f"Test file not found: {test_file}")

    content = test_file.read_text()

    # Find the release_migrations dictionary
    pattern = r'(release_migrations\s*=\s*\{[^}]*)"(\d+\.\d+\.\d+)": "([^"]+)",([^}]*# Add future releases here[^}]*)\}'

    def replace_mapping(match):
        prefix = match.group(1)
        existing_releases = match.group(4)

        # Add the new mapping
        new_mapping = (
            f'            "{release_version}": "{head_revision}",  # Latest release\n'
        )

        return f"{prefix}{new_mapping}{existing_releases}}}"

    # Check if the release already exists
    if f'"{release_version}":' in content:
        print(f"⚠️  Release {release_version} already exists in mapping")
        return False

    new_content = re.sub(pattern, replace_mapping, content, flags=re.DOTALL)

    if new_content != content:
        test_file.write_text(new_content)
        print(
            f"✅ Updated {test_file.name} with mapping: {release_version} -> {head_revision}"
        )
        return True
    print("❌ Could not find release_migrations dictionary to update")
    return False


def main():
    """Main entry point."""
    if len(sys.argv) != 2:
        print("Usage: python update_release_migration_mapping.py <version>")
        print("Example: python update_release_migration_mapping.py 2025.9.1")
        sys.exit(1)

    release_version = sys.argv[1]

    # Validate version format
    if not re.match(r"^\d{4}\.\d+\.\d+$", release_version):
        print(f"❌ Invalid version format: {release_version}")
        print("Expected format: YYYY.M.P (e.g., 2025.9.1)")
        sys.exit(1)

    try:
        # Get current HEAD
        head_revision = get_current_head()
        print(f"📍 Current HEAD migration: {head_revision}")

        # Update test file
        success = update_test_file(release_version, head_revision)

        if success:
            print(f"\n🎉 Successfully updated release mapping for {release_version}")
            print("\nNext steps:")
            print("1. Review the changes in tests/test_migrations.py")
            print("2. Run tests to ensure everything works")
            print("3. Commit the changes with your release")
        else:
            sys.exit(1)

    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
