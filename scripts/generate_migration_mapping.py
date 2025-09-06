#!/usr/bin/env python3
"""
Generate complete migration name mapping from existing chaotic names to clean YYYYMMDD format.
This creates the mapping file used by the Docker entrypoint to fix migration names.
"""

import json
import re
from datetime import datetime, timedelta
from pathlib import Path


def parse_migration_file(file_path: Path) -> dict | None:
    """Parse migration file to extract metadata."""
    try:
        content = file_path.read_text()

        revision_match = re.search(r'revision\s*=\s*[\'"]([^\'"]+)[\'"]', content)
        down_revision_match = re.search(
            r'down_revision\s*=\s*[\'"]([^\'"]*)[\'"]', content
        )
        create_date_match = re.search(r"Create Date:\s*([^\n]+)", content)

        if not revision_match:
            return None

        # Extract description from filename or docstring
        filename = file_path.name
        if "_" in filename:
            desc_part = filename.split("_", 1)[1].replace(".py", "").replace("_", " ")
        else:
            desc_part = "migration"

        return {
            "file": filename,
            "revision": revision_match.group(1),
            "down_revision": down_revision_match.group(1)
            if down_revision_match and down_revision_match.group(1) != "None"
            else None,
            "create_date": create_date_match.group(1).strip()
            if create_date_match
            else None,
            "description": desc_part.strip("_").replace("_", " ").title(),
        }
    except Exception as e:
        print(f"Error parsing {file_path}: {e}")
        return None


def estimate_migration_date(migration: dict, base_date: datetime, index: int) -> str:
    """Estimate when a migration was created based on available info."""

    # If we have a create date, try to parse it
    if migration["create_date"]:
        try:
            # Try different date formats
            for fmt in ["%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"]:
                try:
                    parsed_date = datetime.strptime(migration["create_date"], fmt)
                    return parsed_date.strftime("%Y%m%d")
                except ValueError:
                    continue
        except Exception:
            pass

    # Fallback: assign dates working backwards from base_date
    estimated_date = base_date - timedelta(days=index)
    return estimated_date.strftime("%Y%m%d")


def should_rename_file(filename: str) -> bool:
    """Check if a file should be renamed (doesn't follow YYYYMMDD convention)."""
    # Already follows convention
    if re.match(r"^\d{8}_.*\.py$", filename):
        return False

    # Squashed migrations - keep as is for now
    return "squashed" not in filename.lower()


def generate_new_filename(
    migration: dict, estimated_date: str, used_dates: dict[str, int]
) -> str:
    """Generate a new filename following YYYYMMDD_description.py convention."""

    # Clean up description
    desc = migration["description"].lower()
    desc = re.sub(r"[^\w\s]", "", desc)  # Remove special chars
    desc = re.sub(r"\s+", "_", desc.strip())  # Replace spaces with underscores
    desc = desc[:50]  # Limit length

    # Handle multiple migrations on same date
    if estimated_date in used_dates:
        used_dates[estimated_date] += 1
        suffix = f"_{used_dates[estimated_date]:02d}"
    else:
        used_dates[estimated_date] = 1
        suffix = ""

    return f"{estimated_date}{suffix}_{desc}.py"


def main():
    """Generate the migration mapping file."""
    migrations_dir = Path(__file__).parent.parent / "migrations" / "versions"
    mapping_file = (
        Path(__file__).parent.parent / "migrations" / "migration_name_mapping.json"
    )

    if not migrations_dir.exists():
        print(f"❌ Migrations directory not found: {migrations_dir}")
        return

    print("🔍 Analyzing migration files...")

    # Parse all migration files
    migration_files = list(migrations_dir.glob("*.py"))
    migrations = []

    for file_path in migration_files:
        migration_data = parse_migration_file(file_path)
        if migration_data:
            migrations.append(migration_data)

    print(f"📊 Found {len(migrations)} migration files")

    # Sort by dependency chain to estimate chronological order
    # Simple approach: assume files are roughly in chronological order
    migrations.sort(key=lambda m: m["file"])

    # Generate mappings
    mappings = {}
    used_dates = {}
    base_date = datetime(2025, 9, 6)  # Start from today and work backwards

    for i, migration in enumerate(reversed(migrations)):  # Reverse to work backwards
        if should_rename_file(migration["file"]):
            estimated_date = estimate_migration_date(migration, base_date, i)
            new_filename = generate_new_filename(migration, estimated_date, used_dates)

            mappings[migration["revision"]] = {
                "old_name": migration["file"],
                "new_name": new_filename,
                "description": migration["description"],
                "estimated_date": estimated_date,
                "create_date_raw": migration["create_date"],
            }

            print(f"   📝 {migration['file']} → {new_filename}")

    # Create the complete mapping structure
    mapping_data = {
        "_comment": "Migration name mapping from old chaotic names to clean YYYYMMDD format",
        "_usage": "Before running migrations, check if current HEAD uses old naming and update to new naming",
        "_generated": datetime.now().isoformat(),
        "_total_mappings": len(mappings),
        "mappings": mappings,
        "_strategy": {
            "phase1": "Create mapping file (this file)",
            "phase2": "Add migration checker to Docker entrypoint",
            "phase3": "Rename files gradually in releases",
            "phase4": "Update alembic_version table if needed",
        },
    }

    # Write mapping file
    with open(mapping_file, "w") as f:
        json.dump(mapping_data, f, indent=2, sort_keys=False)

    print(f"\n✅ Generated mapping file: {mapping_file}")
    print(f"📊 Created {len(mappings)} mappings")
    print(f"🔄 {len(migrations) - len(mappings)} files already follow convention")

    print("\n💡 Next steps:")
    print(f"   1. Review the generated mappings in {mapping_file}")
    print("   2. Adjust dates/names if needed")
    print("   3. Add migration checker to Docker entrypoint")
    print("   4. Gradually rename files in future releases")


if __name__ == "__main__":
    main()
