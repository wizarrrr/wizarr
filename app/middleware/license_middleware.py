"""
License validation middleware for Wizarr Plus runtime protection.
Periodically checks license validity and can disable plus features if license becomes invalid.
"""

import os
import threading
from datetime import datetime, timedelta

import structlog
from flask import Flask, g, jsonify, request

from app.services.licensing import license_service

logger = structlog.get_logger(__name__)


class LicenseValidationMiddleware:
    """
    Middleware that performs periodic license validation for Wizarr Plus.

    Features:
    - Periodic license revalidation (configurable interval)
    - Grace period for temporary network issues
    - Plus feature protection
    - License status monitoring
    """

    def __init__(self, app: Flask | None = None):
        self.app = app
        self.last_validation: datetime | None = None
        self.last_validation_success: datetime | None = None
        self.license_valid = False
        self.validation_message = "License not yet validated"
        self.validation_thread: threading.Thread | None = None
        self.shutdown_event = threading.Event()

        # Configuration
        self.validation_interval = int(
            os.getenv("PLUS_LICENSE_CHECK_INTERVAL", "3600")
        )  # 1 hour
        self.grace_period = int(
            os.getenv("PLUS_LICENSE_GRACE_PERIOD", "86400")
        )  # 24 hours
        self.enabled = os.getenv("WIZARR_PLUS_ENABLED", "").lower() in (
            "true",
            "1",
            "yes",
        )

        if app is not None:
            self.init_app(app)

    def init_app(self, app: Flask):
        """Initialize the middleware with Flask app."""
        self.app = app

        if not self.enabled:
            logger.info("Wizarr Plus licensing middleware disabled")
            return

        logger.info(
            "Initializing Wizarr Plus license validation middleware",
            validation_interval=self.validation_interval,
            grace_period=self.grace_period,
        )

        # Initial license validation
        self._validate_license()

        # Start periodic validation thread
        self._start_validation_thread()

        # Register middleware
        app.before_request(self._before_request)

        # Register cleanup on app teardown
        app.teardown_appcontext(self._cleanup)

    def _start_validation_thread(self):
        """Start the background license validation thread."""
        if self.validation_thread and self.validation_thread.is_alive():
            return

        self.shutdown_event.clear()
        self.validation_thread = threading.Thread(
            target=self._validation_worker, daemon=True, name="LicenseValidationWorker"
        )
        self.validation_thread.start()
        logger.info("License validation worker thread started")

    def _validation_worker(self):
        """Background worker that periodically validates the license."""
        while not self.shutdown_event.is_set():
            try:
                # Wait for next validation or shutdown
                if self.shutdown_event.wait(self.validation_interval):
                    break  # Shutdown requested

                logger.debug("Performing periodic license validation")
                self._validate_license()

            except Exception as e:
                logger.error(
                    "Unexpected error in license validation worker", error=str(e)
                )

    def _validate_license(self):
        """Perform license validation and update internal state."""
        try:
            is_valid, message = license_service.verify_plus_license()

            self.last_validation = datetime.utcnow()
            self.license_valid = is_valid
            self.validation_message = message

            if is_valid:
                self.last_validation_success = self.last_validation
                logger.info("License validation successful", message=message)
            else:
                logger.warning("License validation failed", message=message)

        except Exception as e:
            logger.error("License validation error", error=str(e))
            self.last_validation = datetime.utcnow()
            self.license_valid = False
            self.validation_message = f"Validation error: {str(e)}"

    def _is_within_grace_period(self) -> bool:
        """Check if we're still within the grace period after last successful validation."""
        if not self.last_validation_success:
            return False

        grace_end = self.last_validation_success + timedelta(seconds=self.grace_period)
        return datetime.utcnow() < grace_end

    def _should_block_request(self) -> bool:
        """Determine if the current request should be blocked due to license issues."""
        # Always allow if licensing is disabled
        if not self.enabled:
            return False

        # Allow if license is currently valid
        if self.license_valid:
            return False

        # Allow if we're within grace period
        return not self._is_within_grace_period()

    def _is_plus_endpoint(self, endpoint: str) -> bool:
        """Check if the current endpoint requires Plus features."""
        # Add your Plus-specific route patterns here
        plus_patterns = [
            "/plus/",
            "/api/plus/",
            "/hx/plus/",
            "/activity/",
            "/audit/",
        ]

        return any(pattern in endpoint for pattern in plus_patterns)

    def _before_request(self):
        """Flask before_request handler."""
        if not self.enabled:
            return None

        # Add license status to Flask global context
        g.plus_license_valid = self.license_valid
        g.plus_license_message = self.validation_message
        g.plus_within_grace = self._is_within_grace_period()

        # Check if this is a Plus-specific endpoint
        endpoint = request.endpoint or ""
        path = request.path

        # Only protect Plus-specific endpoints
        if not (self._is_plus_endpoint(endpoint) or self._is_plus_endpoint(path)):
            return None

        # Block request if license validation failed and grace period expired
        if self._should_block_request():
            logger.warning(
                "Blocking Plus endpoint access due to invalid license",
                endpoint=endpoint,
                path=path,
                license_valid=self.license_valid,
                within_grace=self._is_within_grace_period(),
            )

            if request.is_json or "application/json" in request.headers.get(
                "Accept", ""
            ):
                return jsonify(
                    {
                        "error": "Plus License Required",
                        "message": "A valid Wizarr Plus license is required to access this feature.",
                        "details": self.validation_message,
                        "support_url": "https://wizarr.dev/plus",
                    }
                ), 402  # Payment Required
            # For HTML requests, you might want to redirect to a license page
            # or render a template explaining the license requirement
            return (
                f"""
                <html>
                <head><title>Plus License Required</title></head>
                <body>
                    <h1>🔐 Plus License Required</h1>
                    <p>A valid Wizarr Plus license is required to access this feature.</p>
                    <p><strong>Status:</strong> {self.validation_message}</p>
                    <p><a href="https://wizarr.dev/plus">Get Wizarr Plus</a></p>
                </body>
                </html>
                """,
                402,
            )

        return None

    def _cleanup(self, error=None):
        """Cleanup resources on app teardown."""
        pass  # Context-specific cleanup if needed

    def shutdown(self):
        """Gracefully shutdown the middleware."""
        logger.info("Shutting down license validation middleware")
        self.shutdown_event.set()

        if self.validation_thread and self.validation_thread.is_alive():
            self.validation_thread.join(timeout=5)

    def get_status(self) -> dict:
        """Get current license validation status."""
        return {
            "enabled": self.enabled,
            "license_valid": self.license_valid,
            "message": self.validation_message,
            "last_validation": self.last_validation.isoformat()
            if self.last_validation
            else None,
            "last_success": self.last_validation_success.isoformat()
            if self.last_validation_success
            else None,
            "within_grace_period": self._is_within_grace_period(),
            "grace_period_seconds": self.grace_period,
            "validation_interval_seconds": self.validation_interval,
        }

    def force_validation(self) -> dict:
        """Force immediate license validation and return status."""
        logger.info("Forcing immediate license validation")
        self._validate_license()
        return self.get_status()


# Global middleware instance
license_middleware = LicenseValidationMiddleware()
