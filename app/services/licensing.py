"""
Keygen license verification service for Wizarr Plus.
Handles runtime license validation and machine fingerprinting.
"""

import base64
import hashlib
import json
import os
import platform
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import requests
import structlog

from app.services.shared.base import BaseService

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class LicenseInfo:
    """License information extracted from verified license key."""

    license_id: str
    product_id: str
    account_id: str
    user_email: str | None
    created_at: datetime
    expires_at: datetime | None
    is_valid: bool
    validation_code: str
    validation_detail: str


class LicenseVerificationError(Exception):
    """Raised when license verification fails."""

    pass


class KeygenLicenseService(BaseService):
    """Service for verifying Keygen licenses at runtime."""

    def __init__(self):
        self.account_id = os.getenv("KEYGEN_ACCOUNT_ID")
        self.api_base = os.getenv("KEYGEN_API_BASE", "https://api.keygen.sh/v1")
        self.license_key = os.getenv("WIZARR_PLUS_LICENSE_KEY")
        self.public_key = os.getenv("KEYGEN_PUBLIC_KEY")
        self.skip_verification = os.getenv("WIZARR_PLUS_LICENSE_SKIP", "").lower() in (
            "true",
            "1",
            "yes",
        )

        if not self.skip_verification and not self.account_id:
            raise LicenseVerificationError(
                "KEYGEN_ACCOUNT_ID environment variable is required"
            )

    def generate_machine_fingerprint(self) -> str:
        """
        Generate a unique fingerprint for the current machine.
        Uses hardware and system information to create a consistent identifier.
        """
        try:
            # Collect system information
            system_info = {
                "hostname": platform.node(),
                "system": platform.system(),
                "machine": platform.machine(),
                "processor": platform.processor(),
            }

            # Try to get additional hardware info (best effort)
            try:
                import uuid

                system_info["node"] = hex(uuid.getnode())
            except Exception:
                pass

            # Create deterministic fingerprint
            fingerprint_data = json.dumps(system_info, sort_keys=True)
            fingerprint = hashlib.sha256(fingerprint_data.encode()).hexdigest()

            logger.info(
                "Generated machine fingerprint", fingerprint=fingerprint[:16] + "..."
            )
            return fingerprint

        except Exception as e:
            logger.error("Failed to generate machine fingerprint", error=str(e))
            # Fallback to hostname-based fingerprint
            hostname = platform.node() or "unknown"
            return hashlib.sha256(hostname.encode()).hexdigest()

    def validate_license_key(self, license_key: str | None = None) -> LicenseInfo:
        """
        Validate a license key with Keygen API.

        Args:
            license_key: License key to validate. If None, uses WIZARR_PLUS_LICENSE_KEY env var.

        Returns:
            LicenseInfo object with validation results

        Raises:
            LicenseVerificationError: If validation fails or API is unreachable
        """
        key = license_key or self.license_key
        if not key:
            raise LicenseVerificationError("No license key provided")

        fingerprint = self.generate_machine_fingerprint()

        # Validate license key with machine fingerprint
        url = (
            f"{self.api_base}/accounts/{self.account_id}/licenses/actions/validate-key"
        )

        payload = {"meta": {"key": key, "scope": {"fingerprint": fingerprint}}}

        headers = {
            "Content-Type": "application/vnd.api+json",
            "Accept": "application/vnd.api+json",
        }

        try:
            logger.info(
                "Validating license key with Keygen", account_id=self.account_id
            )
            response = requests.post(url, json=payload, headers=headers, timeout=30)

            if response.status_code != 200:
                logger.error(
                    "License validation failed",
                    status_code=response.status_code,
                    response=response.text,
                )
                raise LicenseVerificationError(
                    f"License validation failed with status {response.status_code}"
                )

            data = response.json()
            return self._parse_license_response(data)

        except requests.RequestException as e:
            logger.error("Failed to connect to Keygen API", error=str(e))

            # Try offline verification if possible
            if self.public_key:
                logger.info("Attempting offline license verification")
                return self._verify_license_offline(key)

            raise LicenseVerificationError(f"Cannot verify license: {str(e)}") from e

    def _parse_license_response(self, response_data: dict[str, Any]) -> LicenseInfo:
        """Parse Keygen API response into LicenseInfo object."""
        try:
            meta = response_data.get("meta", {})
            data = response_data.get("data", {})
            attributes = data.get("attributes", {})

            # Parse dates
            created_at = datetime.fromisoformat(
                attributes.get("created", "").replace("Z", "+00:00")
            )
            expires_at = None
            if attributes.get("expiry"):
                expires_at = datetime.fromisoformat(
                    attributes.get("expiry", "").replace("Z", "+00:00")
                )

            # Extract user email if available
            user_email = None
            included = response_data.get("included", [])
            for item in included:
                if item.get("type") == "users":
                    user_email = item.get("attributes", {}).get("email")
                    break

            license_info = LicenseInfo(
                license_id=data.get("id", ""),
                product_id=attributes.get("productId", ""),
                account_id=self.account_id,
                user_email=user_email,
                created_at=created_at,
                expires_at=expires_at,
                is_valid=meta.get("valid", False),
                validation_code=meta.get("code", ""),
                validation_detail=meta.get("detail", ""),
            )

            logger.info(
                "License validation completed",
                is_valid=license_info.is_valid,
                code=license_info.validation_code,
                expires_at=license_info.expires_at,
            )

            return license_info

        except Exception as e:
            logger.error("Failed to parse license response", error=str(e))
            raise LicenseVerificationError(
                f"Invalid license response format: {str(e)}"
            ) from e

    def _verify_license_offline(self, license_key: str) -> LicenseInfo:
        """
        Verify license key offline using cryptographic signature.
        Requires KEYGEN_PUBLIC_KEY environment variable.
        """
        if not self.public_key:
            raise LicenseVerificationError(
                "Offline verification requires KEYGEN_PUBLIC_KEY"
            )

        try:
            from Crypto.Hash import SHA256
            from Crypto.PublicKey import RSA
            from Crypto.Signature import PKCS1_v1_5
        except ImportError as e:
            raise LicenseVerificationError(
                "pycryptodome library required for offline verification"
            ) from e

        try:
            # Split license key
            signing_data, enc_sig = license_key.split(".")
            signing_prefix, enc_key = signing_data.split("/")

            # Decode data and signature
            key_data = base64.urlsafe_b64decode(enc_key + "==")  # Add padding if needed
            signature = base64.urlsafe_b64decode(enc_sig + "==")

            # Verify signature
            pub_key = RSA.importKey(self.public_key)
            verifier = PKCS1_v1_5.new(pub_key)
            digest = SHA256.new(data=f"key/{enc_key}".encode())

            is_valid = verifier.verify(digest, signature)

            if not is_valid:
                raise LicenseVerificationError("License signature verification failed")

            # Parse license data
            license_data = json.loads(key_data.decode())

            # Extract license information
            license_info = license_data.get("license", {})
            user_info = license_data.get("user", {})

            created_at = datetime.fromisoformat(
                license_info.get("created", "").replace("Z", "+00:00")
            )
            expires_at = None
            if license_info.get("expiry"):
                expires_at = datetime.fromisoformat(
                    license_info.get("expiry", "").replace("Z", "+00:00")
                )

            # Check if license is expired
            now = datetime.now(UTC)
            is_expired = expires_at and expires_at < now

            return LicenseInfo(
                license_id=license_info.get("id", ""),
                product_id=license_data.get("product", {}).get("id", ""),
                account_id=license_data.get("account", {}).get("id", ""),
                user_email=user_info.get("email"),
                created_at=created_at,
                expires_at=expires_at,
                is_valid=not is_expired,
                validation_code="VALID" if not is_expired else "EXPIRED",
                validation_detail="License verified offline"
                if not is_expired
                else "License has expired",
            )

        except Exception as e:
            logger.error("Offline license verification failed", error=str(e))
            raise LicenseVerificationError(
                f"Offline verification failed: {str(e)}"
            ) from e

    def activate_machine(self, license_key: str | None = None) -> bool:
        """
        Activate the current machine for the license.
        Call this if license validation returns FINGERPRINT_SCOPE_MISMATCH or NO_MACHINES.
        """
        key = license_key or self.license_key
        if not key:
            raise LicenseVerificationError(
                "No license key provided for machine activation"
            )

        fingerprint = self.generate_machine_fingerprint()

        # First validate to get license ID
        license_info = self.validate_license_key(key)

        url = f"{self.api_base}/accounts/{self.account_id}/machines"

        payload = {
            "data": {
                "type": "machines",
                "attributes": {
                    "fingerprint": fingerprint,
                    "name": f"wizarr-plus-{platform.node()}",
                    "platform": platform.system(),
                    "hostname": platform.node(),
                },
                "relationships": {
                    "license": {
                        "data": {"type": "licenses", "id": license_info.license_id}
                    }
                },
            }
        }

        headers = {
            "Content-Type": "application/vnd.api+json",
            "Accept": "application/vnd.api+json",
            "Authorization": f"License {key}",
        }

        try:
            logger.info(
                "Activating machine for license",
                license_id=license_info.license_id,
                fingerprint=fingerprint[:16] + "...",
            )

            response = requests.post(url, json=payload, headers=headers, timeout=30)

            if response.status_code == 201:
                logger.info("Machine activation successful")
                return True
            logger.error(
                "Machine activation failed",
                status_code=response.status_code,
                response=response.text,
            )
            return False

        except requests.RequestException as e:
            logger.error("Failed to activate machine", error=str(e))
            return False

    def verify_plus_license(self) -> tuple[bool, str]:
        """
        Main method to verify Wizarr Plus license.

        Returns:
            Tuple of (is_valid, message)
        """
        # Skip verification in development mode
        if self.skip_verification:
            logger.info("Skipping license verification (development mode)")
            return True, "Development mode - license verification skipped"

        try:
            license_info = self.validate_license_key()

            if not license_info.is_valid:
                # Try machine activation for specific error codes
                if license_info.validation_code in [
                    "FINGERPRINT_SCOPE_MISMATCH",
                    "NO_MACHINES",
                ]:
                    logger.info(
                        "Attempting machine activation",
                        code=license_info.validation_code,
                    )
                    if self.activate_machine():
                        # Re-validate after activation
                        license_info = self.validate_license_key()

                if not license_info.is_valid:
                    return (
                        False,
                        f"License validation failed: {license_info.validation_detail}",
                    )

            # Additional checks
            if license_info.expires_at:
                now = datetime.now(UTC)
                if license_info.expires_at < now:
                    return False, f"License expired on {license_info.expires_at.date()}"

            logger.info(
                "Wizarr Plus license verified successfully",
                license_id=license_info.license_id,
                user_email=license_info.user_email,
            )

            return True, "Valid Wizarr Plus license"

        except LicenseVerificationError as e:
            logger.error("License verification error", error=str(e))
            return False, str(e)
        except Exception as e:
            logger.error("Unexpected license verification error", error=str(e))
            return False, f"License verification failed: {str(e)}"


# Global license service instance
license_service = KeygenLicenseService()
