"""Add suffix to inactive API keys

Revision ID: 20251010_add_suffix_to_inactive_api_keys
Revises: 08a6c8fb44db
Create Date: 2025-10-10 00:00:00.000000

"""

import datetime

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20251010_add_suffix_to_inactive_api_keys"
down_revision = "08a6c8fb44db"
branch_labels = None
depends_on = None


def upgrade():
    """Add suffix to all inactive API keys."""
    
    # Get today's date in YYYY-MM-DD format
    todays_date = datetime.date.today().strftime("%Y-%m-%d")
    suffix = f"-del_{todays_date}"
    
    # Get database connection
    connection = op.get_bind()
    
    # Update all inactive API keys to add the suffix
    # Only update keys that don't already have the suffix to avoid double-suffixing
    result = connection.execute(
        sa.text("""
            UPDATE api_key 
            SET name = name || :suffix
            WHERE is_active = 0 
            AND name NOT LIKE '%' || :suffix
        """),
        {"suffix": suffix}
    )
    
    # Log how many keys were updated
    if result.rowcount > 0:
        print(f"Migration: Added suffix '{suffix}' to {result.rowcount} inactive API key(s)")
    else:
        print("Migration: No inactive API keys found to update")


def downgrade():
    """Remove suffix from API keys that have it."""
    
    # Get today's date in YYYY-MM-DD format (same as used in upgrade)
    todays_date = datetime.now().strftime("%Y%m%d_%H%M%S")
    suffix = f"-del_{todays_date}"
    
    # Get database connection
    connection = op.get_bind()
    
    # Remove the suffix from API key names that have it
    # Use REPLACE to remove the suffix from the end of the name
    result = connection.execute(
        sa.text("""
            UPDATE api_key 
            SET name = REPLACE(name, :suffix, '')
            WHERE name LIKE '%' || :suffix
        """),
        {"suffix": suffix}
    )
    
    # Log how many keys were updated
    if result.rowcount > 0:
        print(f"Migration: Removed suffix '{suffix}' from {result.rowcount} API key(s)")
    else:
        print("Migration: No API keys found with suffix to remove")