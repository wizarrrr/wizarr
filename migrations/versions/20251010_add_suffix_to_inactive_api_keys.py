"""Add suffix to inactive API keys

Revision ID: 20251010_add_suffix_to_inactive_api_keys
Revises: 08a6c8fb44db
Create Date: 2025-10-10 00:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20251010_add_suffix_to_inactive_api_keys"
down_revision = "08a6c8fb44db"
branch_labels = None
depends_on = None


def upgrade():
    """Add suffix to all inactive API keys."""

    # Get database connection
    connection = op.get_bind()

    # Get all inactive API keys that don't already have the -del suffix
    result = connection.execute(
        sa.text("""
            SELECT id, name, created_at
            FROM api_key
            WHERE is_active = 0
            AND name NOT LIKE '%-del'
        """)
    )

    rows = result.fetchall()
    updated_count = 0

    for row in rows:
        api_key_id, current_name, created_at = row

        # created_at is a Python datetime object from SQLAlchemy
        created_timestamp = created_at

        # Format the timestamp to match your application pattern: YYYYMMDD_HHMMSS
        formatted_date = created_timestamp.strftime("%Y%m%d_%H%M%S")
        suffix = f"_{formatted_date}-del"

        # Truncate the original name if the final result would be too long
        # Standard VARCHAR limit is usually 255 characters
        max_name_length = 255 - len(suffix)
        if len(current_name) > max_name_length:
            truncated_name = current_name[:max_name_length]
        else:
            truncated_name = current_name

        new_name = f"{truncated_name}{suffix}"

        # Update this specific API key
        connection.execute(
            sa.text("""
                UPDATE api_key
                SET name = :new_name
                WHERE id = :api_key_id
            """),
            {"new_name": new_name, "api_key_id": api_key_id}
        )

        updated_count += 1

    # Log how many keys were updated
    if updated_count > 0:
        print(f"Migration: Added suffix to {updated_count} inactive API key(s)")
    else:
        print("Migration: No inactive API keys found to update")


def downgrade():
    """Remove suffix from API keys that have it."""

    # Get database connection
    connection = op.get_bind()

    # Get all API keys that end with the timestamp-del pattern
    result = connection.execute(
        sa.text("""
            SELECT id, name
            FROM api_key
            WHERE name LIKE '%_________-del'
            AND LENGTH(name) >= 20
        """)
    )

    rows = result.fetchall()
    updated_count = 0

    for row in rows:
        api_key_id, current_name = row

        # Remove the timestamp suffix using string operations
        # Pattern: _YYYYMMDD_HHMMSS-del (20 characters total)
        if current_name.endswith('-del') and len(current_name) >= 20:
            # Find the last underscore before -del
            suffix_start = current_name.rfind('_', 0, len(current_name) - 4)  # -4 for '-del'
            if suffix_start != -1:
                # Check if it looks like our timestamp pattern
                potential_timestamp = current_name[suffix_start+1:-4]  # Between last _ and -del
                if len(potential_timestamp) == 15 and '_' in potential_timestamp:
                    # Extract the part before our suffix
                    original_name = current_name[:suffix_start]

                    # Update the API key
                    connection.execute(
                        sa.text("""
                            UPDATE api_key
                            SET name = :original_name
                            WHERE id = :api_key_id
                        """),
                        {"original_name": original_name, "api_key_id": api_key_id}
                    )

                    updated_count += 1

    # Log how many keys were updated
    if updated_count > 0:
        print(f"Migration: Removed suffix from {updated_count} API key(s)")
    else:
        print("Migration: No API keys found with suffix to remove")