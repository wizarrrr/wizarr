"""Service for resetting wizard steps to defaults."""

import re
from pathlib import Path

import frontmatter
from flask import current_app
from flask_babel import gettext as _

from app.extensions import db
from app.models import WizardStep


def _strip_jinja_translation(text: str) -> str:
    """Strip Jinja2 translation syntax from text.

    Converts strings like "{{ _('What is Plex?') }}" to "What is Plex?".
    This is used when importing wizard steps to store plain text titles
    instead of template syntax.
    """
    if not text:
        return text

    # Pattern matches {{ _('...') }} or {{ _("...") }}
    pattern = r"\{\{\s*_\(['\"](.+?)['\"]\)\s*\}\}"
    match = re.match(pattern, text.strip())
    if match:
        return match.group(1)

    return text


class WizardResetService:
    """Service to handle resetting wizard steps to defaults."""

    def __init__(self):
        """Initialize the service with the base wizard steps directory."""
        self.base_dir = Path(current_app.root_path).parent / "wizard_steps"

    def _parse_markdown(self, path: Path) -> dict:
        """Parse markdown file with frontmatter (same logic as wizard_seed.py)."""
        post = frontmatter.load(str(path))
        requires = post.get("requires", [])  # list[str]
        title = post.get("title")

        # If no explicit title in front-matter, derive from first markdown header
        if not title:
            for line in post.content.splitlines():
                if line.lstrip().startswith("# "):
                    title = line.lstrip("# ").strip()
                    break

        # Strip Jinja2 translation syntax from title (e.g., "{{ _('...') }}" -> "...")
        # This ensures titles are stored as plain text in the database
        title = _strip_jinja_translation(title)

        return {
            "title": title,
            "markdown": post.content,
            "requires": requires,
        }

    def get_default_steps_for_server(
        self, server_type: str, category: str = "post_invite"
    ) -> list[tuple[str | None, str, list, int, str]]:
        """Get default wizard steps from markdown files for a server type.

        Args:
            server_type: The media server type (plex, jellyfin, etc.)
            category: The category for the steps ('pre_invite' or 'post_invite')

        Returns:
            List of tuples: (title, markdown_content, requires, position, category)
        """
        server_dir = self.base_dir / server_type
        if not server_dir.exists() or not server_dir.is_dir():
            raise ValueError(f"No default steps found for server type: {server_type}")

        steps = []
        md_files = sorted(server_dir.glob("*.md"))

        for idx, md_file in enumerate(md_files):
            meta = self._parse_markdown(md_file)
            steps.append(
                (meta["title"], meta["markdown"], meta["requires"], idx, category)
            )

        return steps

    def reset_server_steps(
        self, server_type: str, category: str = "post_invite"
    ) -> tuple[bool, str, int]:
        """Delete custom steps and reimport defaults for a server type.

        Args:
            server_type: The media server type to reset
            category: The category for the steps ('pre_invite' or 'post_invite')
                     Defaults to 'post_invite' for backward compatibility

        Returns:
            Tuple of (success, message, count)
        """
        try:
            # Delete existing steps for this server type and category
            deleted_count = WizardStep.query.filter_by(
                server_type=server_type, category=category
            ).delete()
            db.session.flush()

            # Expunge all objects from the session to clear the identity map
            # This prevents SQLAlchemy identity map conflicts when creating new
            # WizardStep objects that may reuse the same primary key IDs as the
            # deleted objects (common in SQLite which reuses IDs)
            db.session.expunge_all()

            # Get default steps with the specified category
            default_steps = self.get_default_steps_for_server(server_type, category)

            if not default_steps:
                db.session.rollback()
                return (
                    False,
                    _("No default steps found for server type: {}").format(server_type),
                    0,
                )

            # Import default steps with category
            for title, markdown, requires, position, step_category in default_steps:
                step = WizardStep(
                    server_type=server_type,
                    category=step_category,
                    position=position,
                    title=title,
                    markdown=markdown,
                    requires=requires,
                )
                db.session.add(step)

            db.session.commit()

            return (
                True,
                _("Reset {} steps for {} (deleted {}, imported {})").format(
                    server_type,
                    server_type.capitalize(),
                    deleted_count,
                    len(default_steps),
                ),
                len(default_steps),
            )

        except ValueError as e:
            db.session.rollback()
            return False, str(e), 0
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error resetting wizard steps: {e}")
            return False, _("Failed to reset steps: {}").format(str(e)), 0
