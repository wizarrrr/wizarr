"""Fix wizard step titles by stripping Jinja2 translation syntax.

Revision ID: 20251211_fix_titles
Revises: 20251210_add_wizard_interactions
Create Date: 2025-12-11

This migration fixes existing wizard step titles that were stored with
Jinja2 template syntax like "{{ _('What is Plex?') }}" and converts
them to plain text like "What is Plex?".
"""

import re

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20251211_fix_titles"
down_revision = "20251210_add_wizard_interactions"
branch_labels = None
depends_on = None


def _strip_jinja_translation(text: str) -> str:
    """Strip Jinja2 translation syntax from text.

    Converts strings like "{{ _('What is Plex?') }}" to "What is Plex?".
    """
    if not text:
        return text

    # Pattern matches {{ _('...') }} or {{ _("...") }}
    pattern = r"\{\{\s*_\(['\"](.+?)['\"]\)\s*\}\}"
    match = re.match(pattern, text.strip())
    if match:
        return match.group(1)

    return text


def upgrade():
    """Fix existing wizard step titles with Jinja2 syntax."""
    # Get connection and execute raw SQL to update titles
    connection = op.get_bind()

    # Check if the wizard_step table exists
    inspector = sa.inspect(connection)
    if not inspector.has_table("wizard_step"):
        return

    # Fetch all wizard steps with titles containing Jinja2 syntax
    result = connection.execute(
        sa.text("SELECT id, title FROM wizard_step WHERE title LIKE '%{{ _%'")
    )
    rows = result.fetchall()

    # Update each row with the cleaned title
    for row in rows:
        step_id, title = row
        cleaned_title = _strip_jinja_translation(title)
        if cleaned_title != title:
            connection.execute(
                sa.text("UPDATE wizard_step SET title = :title WHERE id = :id"),
                {"title": cleaned_title, "id": step_id},
            )


def downgrade():
    """No downgrade - this is a data fix that improves user experience."""
    # We don't restore the template syntax as it was unintentional
