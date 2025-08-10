"""Test WebAuthn security restrictions."""

from unittest.mock import patch

import pytest
from flask import Flask

from app.blueprints.webauthn.routes import _validate_secure_origin, get_rp_config


class TestWebAuthnSecurity:
    """Test WebAuthn security restrictions."""

    def test_validate_secure_origin_https_required(self):
        """Test that HTTPS is required."""
        with pytest.raises(ValueError, match="Passkeys require HTTPS"):
            _validate_secure_origin("http://example.com", "example.com")

    def test_validate_secure_origin_domain_required(self):
        """Test that domain names are required (not IP addresses)."""
        # Test IPv4 rejection
        with pytest.raises(ValueError, match="Passkeys require a domain name"):
            _validate_secure_origin("https://192.168.1.1", "192.168.1.1")

        # Test IPv6 rejection
        with pytest.raises(ValueError, match="Passkeys require a domain name"):
            _validate_secure_origin("https://[2001:db8::1]", "2001:db8::1")

        # Test specific IPv6 localhost
        with pytest.raises(ValueError, match="Passkeys require a domain name"):
            _validate_secure_origin("https://[::1]", "::1")

    def test_validate_secure_origin_localhost_development_only(self, app):
        """Test that localhost is only allowed in development."""
        # Test localhost rejection in production (override testing flag)
        with (
            app.app_context(),
            patch.dict("os.environ", {"FLASK_ENV": "production"}),
            patch.object(app, "config", {**app.config, "TESTING": False}),
            pytest.raises(
                ValueError, match="Passkeys cannot use localhost in production"
            ),
        ):
            _validate_secure_origin("https://localhost", "localhost")

        # Test localhost allowed in development
        with app.app_context(), patch.dict("os.environ", {"FLASK_ENV": "development"}):
            # Should not raise an exception
            _validate_secure_origin("https://localhost", "localhost")

    def test_validate_secure_origin_valid_domain(self):
        """Test that valid domains pass validation."""
        # These should all pass without raising exceptions
        _validate_secure_origin("https://example.com", "example.com")
        _validate_secure_origin("https://app.example.com", "app.example.com")
        _validate_secure_origin("https://wizarr.example.org", "wizarr.example.org")
        _validate_secure_origin(
            "https://my-app.example-domain.com", "my-app.example-domain.com"
        )

    def test_validate_secure_origin_invalid_domain_format(self):
        """Test that invalid domain formats are rejected."""
        with pytest.raises(ValueError, match="Invalid domain name format"):
            _validate_secure_origin("https://invalid..domain", "invalid..domain")

        with pytest.raises(ValueError, match="Invalid domain name format"):
            _validate_secure_origin("https://-invalid.domain", "-invalid.domain")

    def test_get_rp_config_environment_override_validation(self, app):
        """Test that environment overrides are validated."""
        with (
            app.app_context(),
            app.test_request_context(),
            patch.dict(
                "os.environ",
                {
                    "WEBAUTHN_RP_ID": "example.com",
                    "WEBAUTHN_ORIGIN": "http://example.com",  # HTTP should fail
                },
            ),
            pytest.raises(ValueError, match="Passkeys require HTTPS"),
        ):
            get_rp_config()

    def test_get_rp_config_request_based_validation(self, app):
        """Test that request-based configuration is validated."""
        # Clear environment variables to force request-based config
        with (
            patch.dict("os.environ", {}, clear=True),
            app.app_context(),
            app.test_request_context("/", headers={"Host": "example.com"}),
            pytest.raises(ValueError, match="Passkeys require HTTPS"),
        ):
            get_rp_config()

        # Test IP address rejection
        with (
            patch.dict("os.environ", {}, clear=True),
            app.app_context(),
            app.test_request_context(
                "/", headers={"Host": "192.168.1.1", "X-Forwarded-Proto": "https"}
            ),
            pytest.raises(ValueError, match="Passkeys require a domain name"),
        ):
            get_rp_config()

    def test_get_rp_config_htmx_url_validation(self, app):
        """Test that HTMX current URL is validated."""
        # Clear environment variables to force request-based config
        with (
            patch.dict("os.environ", {}, clear=True),
            app.app_context(),
            app.test_request_context(
                "/", headers={"HX-Current-URL": "http://example.com/path"}
            ),
            pytest.raises(ValueError, match="Passkeys require HTTPS"),
        ):
            get_rp_config()

        # Test IP address in HX-Current-URL
        with (
            patch.dict("os.environ", {}, clear=True),
            app.app_context(),
            app.test_request_context(
                "/", headers={"HX-Current-URL": "https://192.168.1.1/path"}
            ),
            pytest.raises(ValueError, match="Passkeys require a domain name"),
        ):
            get_rp_config()

    def test_get_rp_config_valid_configuration(self, app):
        """Test that valid configurations work properly."""
        with app.app_context():
            # Test valid environment override
            with (
                patch.dict(
                    "os.environ",
                    {
                        "WEBAUTHN_RP_ID": "example.com",
                        "WEBAUTHN_ORIGIN": "https://example.com",
                    },
                ),
                app.test_request_context(),
            ):
                rp_id, rp_name, origin = get_rp_config()
                assert rp_id == "example.com"
                assert origin == "https://example.com"

            # Test valid request-based config
            with (
                patch.dict("os.environ", {}, clear=True),
                app.test_request_context(
                    "/", headers={"Host": "example.com", "X-Forwarded-Proto": "https"}
                ),
            ):
                rp_id, rp_name, origin = get_rp_config()
                assert rp_id == "example.com"
                assert origin == "https://example.com"

    def test_get_rp_config_localhost_development(self, app):
        """Test that localhost works in development mode."""
        with (
            app.app_context(),
            patch.dict("os.environ", {"FLASK_ENV": "development"}),
            app.test_request_context(
                "/",
                headers={"Host": "localhost:5000", "X-Forwarded-Proto": "https"},
            ),
        ):
            rp_id, rp_name, origin = get_rp_config()
            assert rp_id == "localhost"
            assert origin == "https://localhost:5000"


@pytest.fixture
def app():
    """Create a Flask app for testing."""
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "test-secret-key"
    return app
