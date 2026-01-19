"""End-to-end tests for LDAP admin authentication."""

import contextlib

import pytest
from playwright.sync_api import expect


def setup_lldap_test_data(app):
    """Set up test users and groups in LLDAP for E2E testing."""
    from app.models import LDAPConfiguration
    from app.services.ldap.client import LDAPClient
    from app.services.ldap.encryption import encrypt_credential

    # Create LLDAP configuration pointing to docker-compose LLDAP service
    config = LDAPConfiguration(
        enabled=True,
        server_url="ldap://localhost:3890",
        use_tls=False,  # No TLS for local testing
        verify_cert=False,
        service_account_dn="uid=admin,ou=people,dc=wizarr,dc=test",
        service_account_password_encrypted=encrypt_credential("test_admin_password"),
        user_base_dn="ou=people,dc=wizarr,dc=test",
        user_search_filter="(uid={username})",
        username_attribute="uid",
        email_attribute="mail",
        user_object_class="person",
        group_base_dn="ou=groups,dc=wizarr,dc=test",
        group_object_class="groupOfUniqueNames",
        group_member_attribute="uniqueMember",
        allow_admin_bind=True,
        admin_group_dn="cn=wizarr_admins,ou=groups,dc=wizarr,dc=test",
    )

    # Test connection
    client = LDAPClient(config)
    success, message = client.test_connection()
    if not success:
        pytest.skip(f"LLDAP server not available: {message}")

    # Create test admin user in LLDAP
    try:
        # Delete if exists
        try:
            conn = client._service_connection()
            conn.delete("uid=testadmin,ou=people,dc=wizarr,dc=test")
            conn.unbind()
        except Exception:
            pass  # User doesn't exist

        # Create test admin user - LLDAP needs manual user creation
        conn = client._service_connection()
        user_dn = "uid=testadmin,ou=people,dc=wizarr,dc=test"

        # Create user with minimal attributes that LLDAP supports
        conn.add(
            user_dn,
            ["person"],
            {
                "uid": "testadmin",
                "cn": "Test Admin",
                "sn": "Admin",
                "mail": "testadmin@wizarr.test",
            },
        )

        # Set password using RFC 3062
        conn.extend.standard.modify_password(
            user_dn,
            new_password="TestPass123!",
        )
        conn.unbind()
    except Exception as e:
        pytest.skip(f"Failed to create test user in LLDAP: {e}")

    # Create wizarr_admins group and add test user
    try:
        conn = client._service_connection()
        # Delete group if exists
        with contextlib.suppress(Exception):
            conn.delete("cn=wizarr_admins,ou=groups,dc=wizarr,dc=test")

        # Create group
        conn.add(
            "cn=wizarr_admins,ou=groups,dc=wizarr,dc=test",
            ["groupOfUniqueNames"],
            {
                "cn": "wizarr_admins",
                "uniqueMember": "uid=testadmin,ou=people,dc=wizarr,dc=test",
            },
        )
        conn.unbind()
    except Exception as e:
        pytest.skip(f"Failed to create admin group in LLDAP: {e}")

    return config


@pytest.mark.e2e
def test_ldap_admin_login_flow(page, live_server, app):
    """Test LDAP admin login flow via UI with real LLDAP server."""
    from app.extensions import db
    from app.models import AdminAccount

    with app.app_context():
        # Set up LLDAP with test data
        config = setup_lldap_test_data(app)
        db.session.add(config)
        db.session.commit()

        try:
            # Navigate to login page
            page.goto(f"{live_server.url()}/login")

            # Wait for page to load
            expect(page.locator("h1")).to_contain_text("Login")

            # Check that LDAP option is available in auth method dropdown
            auth_method_select = page.locator("#auth_method")
            expect(auth_method_select).to_be_visible()

            # Select LDAP authentication
            auth_method_select.select_option("ldap")

            # Verify username and password fields are visible
            expect(page.locator("#username")).to_be_visible()
            expect(page.locator("#password")).to_be_visible()

            # Fill in login form with real LDAP credentials
            page.fill("#username", "testadmin")
            page.fill("#password", "TestPass123!")

            # Submit form
            page.click('button[type="submit"]')

            # Wait for redirect to admin dashboard
            page.wait_for_url("**/admin**", timeout=5000)

            # Verify admin account was created
            admin = AdminAccount.query.filter_by(username="testadmin").first()
            assert admin is not None
            assert admin.username == "testadmin"
            assert admin.auth_source == "local"  # Supports dual authentication
            assert admin.email == "testadmin@wizarr.test"
            assert admin.external_id == "uid=testadmin,ou=people,dc=wizarr,dc=test"

        finally:
            # Cleanup
            admin = AdminAccount.query.filter_by(username="testadmin").first()
            if admin:
                db.session.delete(admin)
            db.session.delete(config)
            db.session.commit()

            # Cleanup LLDAP test data
            try:
                from app.services.ldap.client import LDAPClient

                client = LDAPClient(config)
                conn = client._service_connection()
                conn.delete("cn=wizarr_admins,ou=groups,dc=wizarr,dc=test")
                conn.delete("uid=testadmin,ou=people,dc=wizarr,dc=test")
                conn.unbind()
            except Exception:
                pass  # Best effort cleanup


@pytest.mark.e2e
def test_ldap_admin_login_invalid_credentials(page, live_server, app):
    """Test LDAP admin login with invalid credentials using real LLDAP server."""
    from app.extensions import db

    with app.app_context():
        # Set up LLDAP with test data
        config = setup_lldap_test_data(app)
        db.session.add(config)
        db.session.commit()

        try:
            # Navigate to login page
            page.goto(f"{live_server.url()}/login")

            # Wait for page to load
            expect(page.locator("h1")).to_contain_text("Login")

            # Select LDAP authentication
            page.locator("#auth_method").select_option("ldap")

            # Fill in login form with invalid credentials
            page.fill("#username", "testadmin")
            page.fill("#password", "WrongPassword123!")

            # Submit form
            page.click('button[type="submit"]')

            # Wait for error message
            page.wait_for_selector("text=Invalid LDAP credentials", timeout=5000)

            # Verify error message is displayed
            expect(page.locator("text=Invalid LDAP credentials")).to_be_visible()

        finally:
            # Cleanup
            db.session.delete(config)
            db.session.commit()

            # Cleanup LLDAP test data
            try:
                from app.services.ldap.client import LDAPClient

                client = LDAPClient(config)
                conn = client._service_connection()
                conn.delete("cn=wizarr_admins,ou=groups,dc=wizarr,dc=test")
                conn.delete("uid=testadmin,ou=people,dc=wizarr,dc=test")
                conn.unbind()
            except Exception:
                pass  # Best effort cleanup
