#!/usr/bin/env python3
"""
Wizarr Recovery Tool
CLI tool for password reset and passkey removal when admin is locked out.
Designed to work in containerized environments.
"""

import getpass
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Flask app initialization imports - moved here to satisfy E402
from app import create_app  # noqa: E402
from app.extensions import db  # noqa: E402
from app.models import AdminAccount, Settings, WebAuthnCredential  # noqa: E402


def print_banner():
    """Print the recovery tool banner."""
    print("=" * 60)
    print("🔧 WIZARR RECOVERY TOOL")
    print("=" * 60)
    print("This tool helps recover admin access when locked out.")
    print("Use with caution - only run when necessary.")
    print()


def list_admins():
    """List all admin accounts."""
    print("📋 Admin Accounts:")
    print("-" * 40)

    # Multi-admin accounts
    admin_accounts = AdminAccount.query.all()
    if admin_accounts:
        for account in admin_accounts:
            passkey_count = WebAuthnCredential.query.filter_by(
                admin_account_id=account.id
            ).count()
            print(f"  ID: {account.id}")
            print(f"  Username: {account.username}")
            print(f"  Passkeys: {passkey_count}")
            print(f"  Created: {account.created_at}")
            print()

    # Legacy admin (Settings table)
    legacy_username = (
        db.session.query(Settings.value).filter_by(key="admin_username").scalar()
    )
    if legacy_username:
        print("  Legacy Admin:")
        print(f"  Username: {legacy_username}")
        print("  Note: Legacy admin does not support passkeys")
        print()

    if not admin_accounts and not legacy_username:
        print("  No admin accounts found.")
    print()


def reset_admin_password():
    """Reset password for an admin account."""
    print("🔑 Reset Admin Password")
    print("-" * 40)

    # List admins first
    admin_accounts = AdminAccount.query.all()
    if not admin_accounts:
        print("No multi-admin accounts found.")

        # Check for legacy admin
        legacy_username = (
            db.session.query(Settings.value).filter_by(key="admin_username").scalar()
        )
        if legacy_username:
            print(f"Found legacy admin: {legacy_username}")
            choice = input("Reset legacy admin password? (y/N): ").lower()
            if choice == "y":
                new_password = getpass.getpass("Enter new password: ")
                confirm_password = getpass.getpass("Confirm new password: ")

                if new_password != confirm_password:
                    print("❌ Passwords do not match.")
                    return

                if len(new_password) < 6:
                    print("❌ Password must be at least 6 characters long.")
                    return

                from werkzeug.security import generate_password_hash

                password_hash = generate_password_hash(new_password)

                # Update legacy admin password
                admin_password_setting = Settings.query.filter_by(
                    key="admin_password"
                ).first()
                if admin_password_setting:
                    admin_password_setting.value = password_hash
                else:
                    admin_password_setting = Settings(
                        key="admin_password", value=password_hash
                    )
                    db.session.add(admin_password_setting)

                db.session.commit()
                print("✅ Legacy admin password reset successfully.")
        else:
            print("No admin accounts found.")
        return

    # Show admin options
    print("Available admin accounts:")
    for i, account in enumerate(admin_accounts, 1):
        passkey_count = WebAuthnCredential.query.filter_by(
            admin_account_id=account.id
        ).count()
        print(
            f"  {i}. {account.username} (ID: {account.id}, Passkeys: {passkey_count})"
        )

    try:
        choice = int(input("Select admin account (number): ")) - 1
        if choice < 0 or choice >= len(admin_accounts):
            print("❌ Invalid choice.")
            return

        selected_admin = admin_accounts[choice]

        new_password = getpass.getpass("Enter new password: ")
        confirm_password = getpass.getpass("Confirm new password: ")

        if new_password != confirm_password:
            print("❌ Passwords do not match.")
            return

        if len(new_password) < 6:
            print("❌ Password must be at least 6 characters long.")
            return

        selected_admin.set_password(new_password)
        db.session.commit()
        print(f"✅ Password for {selected_admin.username} reset successfully.")

    except ValueError:
        print("❌ Invalid input. Please enter a number.")
    except Exception as e:
        print(f"❌ Error: {e}")


def remove_all_passkeys():
    """Remove all passkeys for an admin account."""
    print("🔐 Remove Admin Passkeys")
    print("-" * 40)

    admin_accounts = AdminAccount.query.all()
    if not admin_accounts:
        print("No multi-admin accounts found.")
        return

    # Show admin options
    print("Available admin accounts:")
    for i, account in enumerate(admin_accounts, 1):
        passkey_count = WebAuthnCredential.query.filter_by(
            admin_account_id=account.id
        ).count()
        print(
            f"  {i}. {account.username} (ID: {account.id}, Passkeys: {passkey_count})"
        )

    try:
        choice = int(input("Select admin account (number): ")) - 1
        if choice < 0 or choice >= len(admin_accounts):
            print("❌ Invalid choice.")
            return

        selected_admin = admin_accounts[choice]
        passkey_count = WebAuthnCredential.query.filter_by(
            admin_account_id=selected_admin.id
        ).count()

        if passkey_count == 0:
            print(f"ℹ️  No passkeys found for {selected_admin.username}.")
            return

        print(
            f"⚠️  This will remove ALL {passkey_count} passkeys for {selected_admin.username}."
        )
        confirm = input("Are you sure? Type 'YES' to confirm: ")

        if confirm == "YES":
            WebAuthnCredential.query.filter_by(
                admin_account_id=selected_admin.id
            ).delete()
            db.session.commit()
            print(f"✅ All passkeys for {selected_admin.username} have been removed.")
        else:
            print("❌ Operation cancelled.")

    except ValueError:
        print("❌ Invalid input. Please enter a number.")
    except Exception as e:
        print(f"❌ Error: {e}")


def create_emergency_admin():
    """Create an emergency admin account."""
    print("🚨 Create Emergency Admin")
    print("-" * 40)

    username = input("Enter username for emergency admin: ").strip()
    if not username:
        print("❌ Username cannot be empty.")
        return

    # Check if username already exists
    if AdminAccount.query.filter_by(username=username).first():
        print(f"❌ Username '{username}' already exists.")
        return

    password = getpass.getpass("Enter password: ")
    confirm_password = getpass.getpass("Confirm password: ")

    if password != confirm_password:
        print("❌ Passwords do not match.")
        return

    if len(password) < 6:
        print("❌ Password must be at least 6 characters long.")
        return

    try:
        emergency_admin = AdminAccount()
        emergency_admin.username = username
        emergency_admin.set_password(password)

        db.session.add(emergency_admin)
        db.session.commit()

        print(f"✅ Emergency admin '{username}' created successfully.")
        print("   You can now login with this account.")

    except Exception as e:
        print(f"❌ Error creating emergency admin: {e}")


def main():
    """Main recovery tool interface."""
    print_banner()

    try:
        # Initialize Flask app
        app = create_app()

        with app.app_context():
            while True:
                print("🔧 Recovery Options:")
                print("1. List all admin accounts")
                print("2. Reset admin password")
                print("3. Remove all passkeys for admin")
                print("4. Create emergency admin account")
                print("5. Exit")
                print()

                choice = input("Select option (1-5): ").strip()

                if choice == "1":
                    list_admins()
                elif choice == "2":
                    reset_admin_password()
                elif choice == "3":
                    remove_all_passkeys()
                elif choice == "4":
                    create_emergency_admin()
                elif choice == "5":
                    print("👋 Goodbye!")
                    break
                else:
                    print("❌ Invalid choice. Please select 1-5.")

                print()

    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
