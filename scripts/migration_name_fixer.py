#!/usr/bin/env python3
"""
Migration name fixer for Docker entrypoint.

This script checks if the current database HEAD uses old chaotic naming
and updates the alembic_version table to use the new clean naming convention.

This allows us to gradually rename migration files without breaking existing deployments.
"""

import json
import sqlite3
import sys
from pathlib import Path


def load_migration_mapping() -> dict:
    """Load the migration name mapping file."""
    mapping_file = (
        Path(__file__).parent.parent / "migrations" / "migration_name_mapping.json"
    )

    if not mapping_file.exists():
        print("ℹ️  No migration mapping file found, skipping name fixes")
        return {}

    try:
        with open(mapping_file) as f:
            data = json.load(f)
            return data.get("mappings", {})
    except Exception as e:
        print(f"⚠️  Could not load migration mapping: {e}")
        return {}


def get_current_head_from_db(db_path: str) -> str | None:
    """Get the current HEAD revision from the alembic_version table."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT version_num FROM alembic_version")
        result = cursor.fetchone()

        conn.close()

        if result:
            return result[0]
        return None
    except Exception as e:
        print(f"⚠️  Could not read alembic_version table: {e}")
        return None


def update_head_in_db(db_path: str, old_revision: str, new_revision: str) -> bool:
    """Update the HEAD revision in the alembic_version table."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Update the version
        cursor.execute(
            "UPDATE alembic_version SET version_num = ? WHERE version_num = ?",
            (new_revision, old_revision),
        )

        if cursor.rowcount > 0:
            conn.commit()
            conn.close()
            return True
        conn.close()
        return False
    except Exception as e:
        print(f"❌ Could not update alembic_version table: {e}")
        return False


def extract_revision_from_filename(filename: str) -> str:
    """Extract revision ID from new filename format."""
    # For new format like "20250905_add_feature.py", the revision ID
    # is embedded in the mapping. We need to reverse-lookup.
    return filename.split("_")[0] if "_" in filename else filename.replace(".py", "")


def check_and_fix_migration_names(db_path: str) -> bool:
    """Main function to check and fix migration names."""
    print("🔍 Checking migration names...")

    # Load mapping
    mappings = load_migration_mapping()
    if not mappings:
        print("ℹ️  No mappings to apply")
        return True

    # Get current HEAD
    current_head = get_current_head_from_db(db_path)
    if not current_head:
        print("ℹ️  No current HEAD found in database")
        return True

    print(f"📍 Current HEAD: {current_head}")

    # Check if current HEAD needs fixing
    if current_head in mappings:
        mapping = mappings[current_head]
        old_name = mapping["old_name"]
        new_name = mapping["new_name"]

        print(f"🔄 Found mapping: {old_name} → {new_name}")

        # For this implementation, we'll keep the same revision ID but log the mapping
        # In the future, we could update the revision ID if we also rename the files
        print(f"✅ Migration name mapping available: {current_head}")
        print(f"   Old file: {old_name}")
        print(f"   New file: {new_name}")
        print(f"   Description: {mapping['description']}")

        # For now, we just log the mapping without changing the DB
        # The actual file renaming will happen gradually in releases
        return True
    print("✅ Current HEAD uses clean naming or no mapping needed")
    return True


def main():
    """Main entry point for Docker entrypoint."""
    if len(sys.argv) != 2:
        print("Usage: python migration_name_fixer.py <database_path>")
        sys.exit(1)

    db_path = sys.argv[1]

    if not Path(db_path).exists():
        print(f"📝 Database file doesn't exist yet: {db_path}")
        print("ℹ️  This is normal for first-time setup")
        sys.exit(0)

    try:
        success = check_and_fix_migration_names(db_path)
        if success:
            print("✅ Migration name check completed successfully")
            sys.exit(0)
        else:
            print("❌ Migration name check failed")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
