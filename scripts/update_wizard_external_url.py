#!/usr/bin/env python3
"""
Script to manually update wizard steps to use dynamic external_url variable.

This script replaces {{ settings.external_url or "" }} with {{ external_url or "" }}
in all WizardStep records in the database.

NOTE: This migration now runs automatically on app startup. This script is provided
for manual execution or troubleshooting purposes only.

Usage:
    python scripts/update_wizard_external_url.py
"""

import os
import sys

# Add the app directory to the path so we can import the app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def update_wizard_steps():
    """Update wizard steps to use the new external_url variable"""
    try:
        from app import create_app
        from app.services.wizard_migration import update_wizard_external_url_references

        app = create_app()

        with app.app_context():
            print("Running wizard step external_url migration...")
            success, message = update_wizard_external_url_references()

            if success:
                print(f"✅ {message}")
            else:
                print(f"❌ {message}")

            return success

    except ImportError as e:
        print(f"❌ Could not import app modules: {e}")
        print("Make sure you're running this from the Wizarr root directory")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


if __name__ == "__main__":
    print("🧙‍♂️ Wizarr Wizard Step External URL Updater (Manual)")
    print("=" * 55)
    print("NOTE: This migration now runs automatically on app startup.")
    print("This script is for manual execution or troubleshooting only.")
    print("")

    success = update_wizard_steps()

    if success:
        print('\n🎉 All done! Wizard steps now use {{ external_url or "" }}')
        print("This provides server-specific URLs for multi-server setups.")
    else:
        print("\n💥 Update failed. Please check the error messages above.")
        sys.exit(1)
