"""Update wizard steps to use dynamic external_url variable

Revision ID: 20250712_update_wizard_external_url
Revises:
Create Date: 2025-07-12

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20250712_update_wizard_external_url"
down_revision = "20250705_add_admin_account_table"
branch_labels = None
depends_on = None


def upgrade():
    """Replace {{ settings.external_url or "" }} with {{ external_url or "" }} in wizard steps"""

    # Get database connection
    connection = op.get_bind()

    # Update WizardStep table
    try:
        # Check if the wizard_step table exists
        result = connection.execute(
            sa.text("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='wizard_step'
        """)
        )

        if result.fetchone():
            # Update markdown content in wizard_step table
            connection.execute(
                sa.text("""
                UPDATE wizard_step
                SET markdown = REPLACE(
                    markdown,
                    '{{ settings.external_url or "" }}',
                    '{{ external_url or "" }}'
                )
                WHERE markdown LIKE '%{{ settings.external_url or ""%'
            """)
            )

            # Also replace without spaces around 'or'
            connection.execute(
                sa.text("""
                UPDATE wizard_step
                SET markdown = REPLACE(
                    markdown,
                    '{{ settings.external_url or"" }}',
                    '{{ external_url or "" }}'
                )
                WHERE markdown LIKE '%{{ settings.external_url or""%'
            """)
            )

            # Also replace with single quotes
            connection.execute(
                sa.text("""
                UPDATE wizard_step
                SET markdown = REPLACE(
                    markdown,
                    "{{ settings.external_url or '' }}",
                    '{{ external_url or "" }}'
                )
                WHERE markdown LIKE "%{{ settings.external_url or ''%"
            """)
            )

            print("Updated wizard_step table external_url references")
        else:
            print("wizard_step table does not exist, skipping database updates")

    except Exception as e:
        print(f"Error updating wizard_step table: {e}")
        # Don't fail the migration for this, as it's not critical
        pass


def downgrade():
    """Revert {{ external_url or "" }} back to {{ settings.external_url or "" }} in wizard steps"""

    # Get database connection
    connection = op.get_bind()

    # Revert WizardStep table
    try:
        # Check if the wizard_step table exists
        result = connection.execute(
            sa.text("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='wizard_step'
        """)
        )

        if result.fetchone():
            # Revert markdown content in wizard_step table
            connection.execute(
                sa.text("""
                UPDATE wizard_step
                SET markdown = REPLACE(
                    markdown,
                    '{{ external_url or "" }}',
                    '{{ settings.external_url or "" }}'
                )
                WHERE markdown LIKE '%{{ external_url or ""%'
            """)
            )

            print("Reverted wizard_step table external_url references")
        else:
            print("wizard_step table does not exist, skipping database revert")

    except Exception as e:
        print(f"Error reverting wizard_step table: {e}")
        pass
