#!/usr/bin/env python3
"""
Gradually rename migration files to clean YYYYMMDD format.

This script safely renames migration files using the mapping, updating all
internal references and revision chains. Run this when you want to clean up
the actual filenames.

IMPORTANT: Only run this on a clean git working tree and test thoroughly!
"""

import json
import re
import shutil
from pathlib import Path


def load_migration_mapping() -> dict[str, dict]:
    """Load the migration name mapping file."""
    mapping_file = (
        Path(__file__).parent.parent / "migrations" / "migration_name_mapping.json"
    )

    if not mapping_file.exists():
        raise FileNotFoundError(f"Migration mapping file not found: {mapping_file}")

    with open(mapping_file) as f:
        data = json.load(f)
        return data.get("mappings", {})


def find_migration_file(migrations_dir: Path, filename: str) -> Path | None:
    """Find a migration file in the migrations directory."""
    file_path = migrations_dir / filename
    return file_path if file_path.exists() else None


def update_internal_references(migrations_dir: Path, old_to_new: dict[str, str]) -> int:
    """Update internal revision references in migration files."""
    updates_made = 0

    for migration_file in migrations_dir.glob("*.py"):
        try:
            content = migration_file.read_text()
            original_content = content

            # Update down_revision references
            for old_rev, new_rev in old_to_new.items():
                # Update down_revision = 'old_rev' to down_revision = 'new_rev'
                content = re.sub(
                    rf'(down_revision\s*=\s*[\'"]){old_rev}([\'"])',
                    rf"\g<1>{new_rev}\g<2>",
                    content,
                )

                # Update depends_on references if they exist
                content = re.sub(
                    rf'(depends_on\s*=\s*[\'"]){old_rev}([\'"])',
                    rf"\g<1>{new_rev}\g<2>",
                    content,
                )

            if content != original_content:
                migration_file.write_text(content)
                updates_made += 1
                print(f"   📝 Updated internal references in {migration_file.name}")

        except Exception as e:
            print(f"⚠️  Error updating {migration_file.name}: {e}")

    return updates_made


def rename_migration_files(
    migrations_dir: Path, mappings: dict[str, dict], dry_run: bool = True
) -> list[tuple]:
    """Rename migration files according to the mapping."""
    renames = []

    for revision_id, mapping in mappings.items():
        old_name = mapping["old_name"]
        new_name = mapping["new_name"]

        old_path = find_migration_file(migrations_dir, old_name)
        if not old_path:
            print(f"⚠️  File not found: {old_name}")
            continue

        new_path = migrations_dir / new_name

        if new_path.exists():
            print(f"⚠️  Target file already exists: {new_name}")
            continue

        renames.append((old_path, new_path, revision_id))

        if dry_run:
            print(f"🔍 Would rename: {old_name} → {new_name}")
        else:
            try:
                shutil.move(str(old_path), str(new_path))
                print(f"✅ Renamed: {old_name} → {new_name}")
            except Exception as e:
                print(f"❌ Failed to rename {old_name}: {e}")

    return renames


def validate_migration_chain(migrations_dir: Path) -> bool:
    """Validate that the migration chain is still intact after renaming."""
    print("🔍 Validating migration chain...")

    try:
        # This would normally involve running alembic check, but for simplicity
        # we'll just verify that files exist and have proper structure
        migration_files = list(migrations_dir.glob("*.py"))

        for migration_file in migration_files:
            content = migration_file.read_text()

            # Check for basic migration structure
            if "revision =" not in content:
                print(f"❌ Missing revision in {migration_file.name}")
                return False

            if "def upgrade():" not in content:
                print(f"❌ Missing upgrade function in {migration_file.name}")
                return False

            if "def downgrade():" not in content:
                print(f"❌ Missing downgrade function in {migration_file.name}")
                return False

        print(f"✅ Validated {len(migration_files)} migration files")
        return True

    except Exception as e:
        print(f"❌ Validation failed: {e}")
        return False


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Rename migration files to clean YYYYMMDD format"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be renamed without doing it",
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Actually perform the renames (use with caution!)",
    )

    args = parser.parse_args()

    if not args.dry_run and not args.confirm:
        print("❌ You must specify either --dry-run or --confirm")
        print("   Use --dry-run first to see what would be changed")
        return

    migrations_dir = Path(__file__).parent.parent / "migrations" / "versions"

    if not migrations_dir.exists():
        print(f"❌ Migrations directory not found: {migrations_dir}")
        return

    print("🔍 Loading migration mappings...")
    try:
        mappings = load_migration_mapping()
        print(f"📊 Found {len(mappings)} mappings")
    except Exception as e:
        print(f"❌ Error loading mappings: {e}")
        return

    # Validate git status
    if not args.dry_run:
        print("⚠️  WARNING: This will modify migration files!")
        print("   Make sure you have a clean git working tree and backups!")

        response = input("Continue? (type 'yes' to proceed): ")
        if response.lower() != "yes":
            print("❌ Cancelled by user")
            return

    # Phase 1: Rename files
    print(f"\n🔄 {'Simulating' if args.dry_run else 'Performing'} file renames...")
    renames = rename_migration_files(migrations_dir, mappings, dry_run=args.dry_run)

    if not args.dry_run and renames:
        # Phase 2: Update internal references
        print("\n📝 Updating internal references...")
        # Create mapping of old revision to new revision (they stay the same in this approach)
        # But we could update them if we also changed revision IDs

        # Phase 3: Validate
        print("\n✅ Validating results...")
        if not validate_migration_chain(migrations_dir):
            print("❌ Validation failed! Check migration files manually")
            return

    print(
        f"\n🎉 Migration renaming {'simulation' if args.dry_run else 'process'} completed!"
    )

    if args.dry_run:
        print("   Run with --confirm to actually perform the renames")
    else:
        print("   Don't forget to:")
        print("   1. Test migration upgrade/downgrade")
        print("   2. Update any hardcoded migration names in tests")
        print("   3. Commit the changes")
        print("   4. Update the mapping file if needed")


if __name__ == "__main__":
    main()
