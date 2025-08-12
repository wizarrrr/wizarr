"""
Wizard Step Migration Service

This module handles automatic migration of wizard steps to use dynamic variables.
It runs during app startup to ensure wizard steps are always up-to-date.
"""

import logging

logger = logging.getLogger(__name__)


def update_wizard_external_url_references() -> tuple[bool, str]:
    """
    Update wizard steps to use dynamic external_url variable instead of static settings.external_url.

    Returns:
        Tuple[bool, str]: (success, message)
    """
    try:
        from app.extensions import db
        from app.models import WizardStep

        # Check if WizardStep table exists (might not exist during initial setup)
        try:
            # Test if we can query the table
            WizardStep.query.count()
        except Exception as e:
            logger.debug(f"WizardStep table not available, skipping migration: {e}")
            return True, "WizardStep table not available, skipping migration"

        # Find all wizard steps that contain the old pattern
        steps_with_old_pattern = WizardStep.query.filter(
            WizardStep.markdown.like("%{{ settings.external_url%")
        ).all()

        if not steps_with_old_pattern:
            logger.debug(
                "No wizard steps found with legacy {{ settings.external_url }} pattern"
            )
            return True, "No wizard steps needed updating"

        updated_count = 0

        logger.info(f"Found {len(steps_with_old_pattern)} wizard steps to update")

        for step in steps_with_old_pattern:
            original_markdown = step.markdown

            # Replace various patterns of settings.external_url with external_url
            replacements = [
                ('{{ settings.external_url or "" }}', '{{ external_url or "" }}'),
                ('{{ settings.external_url or"" }}', '{{ external_url or "" }}'),
                ("{{ settings.external_url or '' }}", '{{ external_url or "" }}'),
                ('{{settings.external_url or ""}}', '{{ external_url or "" }}'),
                ('{{settings.external_url or""}}', '{{ external_url or "" }}'),
                ("{{settings.external_url or ''}}", '{{ external_url or "" }}'),
                ("{{ settings.external_url}}", "{{ external_url }}"),
                ("{{settings.external_url}}", "{{ external_url }}"),
            ]

            for old_pattern, new_pattern in replacements:
                step.markdown = step.markdown.replace(old_pattern, new_pattern)

            # Track if this step was actually changed
            if step.markdown != original_markdown:
                updated_count += 1
                logger.debug(
                    f"Updated wizard step {step.id} ({step.server_type}): {step.title or 'Untitled'}"
                )

        # Save changes if any were made
        if updated_count > 0:
            try:
                db.session.commit()
                message = f"Successfully updated {updated_count} wizard steps to use dynamic external_url"
                logger.info(message)
                return True, message
            except Exception as e:
                db.session.rollback()
                error_msg = f"Failed to save wizard step updates: {e}"
                logger.error(error_msg)
                return False, error_msg
        else:
            logger.debug(
                "All wizard steps already use the correct external_url pattern"
            )
            return True, "All wizard steps already up-to-date"

    except Exception as e:
        error_msg = f"Unexpected error during wizard step migration: {e}"
        logger.error(error_msg, exc_info=True)
        return False, error_msg


def run_wizard_migrations() -> bool:
    """
    Run all wizard-related migrations during app startup.

    Returns:
        bool: True if all migrations succeeded, False otherwise
    """
    try:
        # Skip migrations during testing to avoid side effects
        import os

        if os.environ.get("TESTING") == "True":
            logger.debug("Skipping wizard migrations during testing")
            return True

        logger.debug("Running wizard step migrations...")

        # Update external_url references
        success, message = update_wizard_external_url_references()
        if not success:
            logger.error(f"Wizard migration failed: {message}")
            return False

        logger.debug("Wizard step migrations completed successfully")
        return True

    except Exception as e:
        logger.error(f"Critical error during wizard migrations: {e}", exc_info=True)
        return False
