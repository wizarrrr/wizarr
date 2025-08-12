import base64
import os

from flask import (
    Blueprint,
    current_app,
    jsonify,
    render_template,
    request,
    session,
    url_for,
)
from flask_login import current_user, login_required
from webauthn import (
    generate_authentication_options,
    generate_registration_options,
    verify_authentication_response,
    verify_registration_response,
)
from webauthn.helpers import (
    parse_authentication_credential_json,
    parse_registration_credential_json,
)
from webauthn.helpers.cose import COSEAlgorithmIdentifier
from webauthn.helpers.structs import (
    AuthenticatorSelectionCriteria,
    PublicKeyCredentialDescriptor,
    UserVerificationRequirement,
)

from app.extensions import db, limiter
from app.models import AdminAccount, WebAuthnCredential

webauthn_bp = Blueprint("webauthn", __name__)


def get_rp_config():
    """Get WebAuthn RP configuration based on current request."""
    from urllib.parse import urlparse

    from flask import request

    # Environment overrides
    env_rp_id = os.environ.get("WEBAUTHN_RP_ID")
    env_rp_name = os.environ.get("WEBAUTHN_RP_NAME", "Wizarr")
    env_origin = os.environ.get("WEBAUTHN_ORIGIN")

    if env_rp_id and env_origin:
        # Validate environment variables for security
        _validate_secure_origin(env_origin, env_rp_id)
        return env_rp_id, env_rp_name, env_origin

    # For HTMX requests, prefer HX-Current-URL header
    current_url = request.headers.get("HX-Current-URL")
    if current_url:
        parsed = urlparse(current_url)
        hostname = parsed.hostname
        origin = f"{parsed.scheme}://{parsed.netloc}"
    else:
        host = request.headers.get("Host", "localhost:5000")

        # Detect HTTPS from reverse proxy headers
        is_https = (
            request.is_secure
            or request.headers.get("X-Forwarded-Proto", "").lower() == "https"
            or request.headers.get("X-Forwarded-Ssl", "").lower() == "on"
            or request.headers.get("X-Url-Scheme", "").lower() == "https"
            or request.headers.get("X-Forwarded-Protocol", "").lower() == "https"
        )

        scheme = "https" if is_https else "http"
        hostname = host.split(":")[0]
        origin = f"{scheme}://{host}"

    # Validate the configuration meets security requirements
    _validate_secure_origin(origin, hostname)

    return hostname, env_rp_name, origin


def _validate_secure_origin(origin, rp_id):
    """Validate that the origin and RP ID meet security requirements for passkeys."""
    import re
    from urllib.parse import urlparse

    # Parse the origin
    parsed_origin = urlparse(origin)

    # Requirement 1: Must use HTTPS
    if parsed_origin.scheme != "https":
        raise ValueError(
            "Passkeys require HTTPS. Current origin uses HTTP. "
            "Please configure your application to use HTTPS or set WEBAUTHN_ORIGIN environment variable."
        )

    # Requirement 2: Must use a proper domain name (not IP address)
    hostname = parsed_origin.hostname or rp_id

    # Check if it's an IP address (IPv4 or IPv6) using Python's built-in validation
    import ipaddress

    try:
        # This will succeed if hostname is a valid IP address
        ipaddress.ip_address(hostname)
        raise ValueError(
            f"Passkeys require a domain name, not an IP address. "
            f"Current hostname '{hostname}' is an IP address. "
            f"Please use a proper domain name or set WEBAUTHN_RP_ID and WEBAUTHN_ORIGIN environment variables."
        )
    except ValueError as e:
        # If it's not a valid IP address, that's good (unless it's the error we just raised)
        if "domain name, not an IP address" in str(e):
            raise
        # If it's not a valid IP address, continue with domain validation

    # Check for localhost (only allow in development or testing)
    if hostname in ["localhost", "127.0.0.1", "::1"]:
        import os

        from flask import current_app

        is_development = os.environ.get("FLASK_ENV") == "development"
        is_testing = current_app.config.get("TESTING", False)

        if not (is_development or is_testing):
            raise ValueError(
                f"Passkeys cannot use localhost in production. "
                f"Current hostname '{hostname}' is localhost. "
                f"Please use a proper domain name or set WEBAUTHN_RP_ID and WEBAUTHN_ORIGIN environment variables."
            )

    # Additional validation: ensure it's a valid domain format
    domain_pattern = r"^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$"
    if not re.match(domain_pattern, hostname) and hostname not in ["localhost"]:
        raise ValueError(
            f"Invalid domain name format: '{hostname}'. "
            f"Please use a valid domain name or set WEBAUTHN_RP_ID and WEBAUTHN_ORIGIN environment variables."
        )


@webauthn_bp.route("/webauthn/register/begin", methods=["POST"])
@login_required
def register_begin():
    """Begin WebAuthn registration process."""
    if not isinstance(current_user, AdminAccount):
        return jsonify({"error": "Only admin accounts can register passkeys"}), 403

    try:
        rp_id, rp_name, _ = get_rp_config()
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    if not rp_id:
        return jsonify({"error": "RP ID is required"}), 500

    user_id = str(current_user.id).encode("utf-8")
    current_user.username.encode("utf-8")

    existing_credentials = WebAuthnCredential.query.filter_by(
        admin_account_id=current_user.id
    ).all()
    exclude_credentials = [
        PublicKeyCredentialDescriptor(id=cred.credential_id)
        for cred in existing_credentials
    ]

    registration_options = generate_registration_options(
        rp_id=rp_id,
        rp_name=rp_name,
        user_id=user_id,
        user_name=current_user.username,
        user_display_name=current_user.username,
        exclude_credentials=exclude_credentials,
        authenticator_selection=AuthenticatorSelectionCriteria(
            user_verification=UserVerificationRequirement.PREFERRED,
        ),
        supported_pub_key_algs=[
            COSEAlgorithmIdentifier.ECDSA_SHA_256,
            COSEAlgorithmIdentifier.RSASSA_PKCS1_v1_5_SHA_256,
        ],
    )

    session["webauthn_challenge"] = registration_options.challenge
    session["webauthn_user_id"] = user_id

    return jsonify(registration_options)


@webauthn_bp.route("/webauthn/register/complete", methods=["POST"])
@login_required
def register_complete():
    """Complete WebAuthn registration process."""
    if not isinstance(current_user, AdminAccount):
        return jsonify({"error": "Only admin accounts can register passkeys"}), 403

    credential_data = request.get_json()
    challenge = session.get("webauthn_challenge")
    expected_user_id = session.get("webauthn_user_id")
    passkey_name = session.get("passkey_name")

    if not challenge or not expected_user_id:
        return jsonify({"error": "No registration in progress"}), 400

    try:
        credential = parse_registration_credential_json(credential_data["credential"])
        try:
            rp_id, _, origin = get_rp_config()
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        if not rp_id:
            return jsonify({"error": "RP ID is required"}), 500
        verification = verify_registration_response(
            credential=credential,
            expected_challenge=challenge,
            expected_origin=origin,
            expected_rp_id=rp_id,
        )

        credential_name = passkey_name or credential_data.get(
            "name", f"Passkey {len(current_user.webauthn_credentials) + 1}"
        )

        new_credential = WebAuthnCredential(
            admin_account_id=current_user.id,
            credential_id=verification.credential_id,
            public_key=verification.credential_public_key,
            sign_count=verification.sign_count,
            name=credential_name,
        )

        db.session.add(new_credential)
        db.session.commit()

        # Clean up session data
        session.pop("webauthn_challenge", None)
        session.pop("webauthn_user_id", None)
        session.pop("passkey_name", None)

        return jsonify(
            {
                "verified": True,
                "credential_id": base64.b64encode(verification.credential_id).decode(
                    "utf-8"
                ),
                "name": credential_name,
            }
        )

    except Exception as e:
        # Log the full error for debugging
        import traceback

        current_app.logger.error(f"WebAuthn registration error: {str(e)}")
        current_app.logger.debug(f"Traceback: {traceback.format_exc()}")
        return jsonify({"error": f"Registration failed: {str(e)}"}), 400


@webauthn_bp.route("/webauthn/authenticate/begin", methods=["POST"])
@limiter.limit("20 per minute")
def authenticate_begin():
    """Begin WebAuthn authentication process (usernameless or 2FA)."""
    try:
        rp_id, _, _ = get_rp_config()
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    if not rp_id:
        return jsonify({"error": "RP ID is required"}), 500

    # Check if this is a 2FA authentication
    from flask import session

    pending_2fa_user_id = session.get("pending_2fa_user_id")

    if pending_2fa_user_id:
        # 2FA mode - only get credentials for the specific user
        user_credentials = WebAuthnCredential.query.filter_by(
            admin_account_id=pending_2fa_user_id
        ).all()
        if not user_credentials:
            return jsonify({"error": "No passkeys registered for this user"}), 404
        allow_credentials = [
            PublicKeyCredentialDescriptor(id=cred.credential_id)
            for cred in user_credentials
        ]
    else:
        # Usernameless mode - get all credentials from all admin accounts
        all_credentials = WebAuthnCredential.query.all()
        if not all_credentials:
            return jsonify({"error": "No passkeys registered"}), 404
        allow_credentials = [
            PublicKeyCredentialDescriptor(id=cred.credential_id)
            for cred in all_credentials
        ]

    authentication_options = generate_authentication_options(
        rp_id=rp_id,
        allow_credentials=allow_credentials,
        user_verification=UserVerificationRequirement.PREFERRED,
    )

    session["webauthn_challenge"] = authentication_options.challenge

    # Convert to JSON-serializable format
    def base64url_encode(data):
        return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")

    return jsonify(
        {
            "challenge": base64url_encode(authentication_options.challenge),
            "timeout": authentication_options.timeout,
            "rpId": authentication_options.rp_id,
            "allowCredentials": [
                {
                    "id": base64url_encode(cred.id),
                    "type": cred.type,
                    "transports": list(cred.transports)
                    if hasattr(cred, "transports") and cred.transports
                    else [],
                }
                for cred in (authentication_options.allow_credentials or [])
            ],
            "userVerification": authentication_options.user_verification,
        }
    )


@webauthn_bp.route("/webauthn/authenticate/complete", methods=["POST"])
@limiter.limit("20 per minute")
def authenticate_complete():
    """Complete WebAuthn authentication process (usernameless or 2FA)."""
    credential_data = request.get_json()
    challenge = session.get("webauthn_challenge")

    if not challenge:
        return jsonify({"error": "No authentication in progress"}), 400

    try:
        credential = parse_authentication_credential_json(credential_data["credential"])

        # Find the credential by credential_id
        db_credential = WebAuthnCredential.query.filter_by(
            credential_id=credential.raw_id
        ).first()

        if not db_credential:
            return jsonify({"error": "Credential not found"}), 404

        # Check if this is 2FA authentication
        pending_2fa_user_id = session.get("pending_2fa_user_id")

        if (
            pending_2fa_user_id
            and db_credential.admin_account_id != pending_2fa_user_id
        ):
            # 2FA mode - verify the credential belongs to the pending user
            return jsonify(
                {"error": "Credential does not belong to authenticated user"}
            ), 403

        # Get the admin account associated with this credential
        admin_account = db_credential.admin_account

        try:
            rp_id, _, origin = get_rp_config()
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        if not rp_id:
            return jsonify({"error": "RP ID is required"}), 500
        verification = verify_authentication_response(
            credential=credential,
            expected_challenge=challenge,
            expected_origin=origin,
            expected_rp_id=rp_id,
            credential_public_key=db_credential.public_key,
            credential_current_sign_count=db_credential.sign_count,
        )

        # Update credential usage
        db_credential.sign_count = verification.new_sign_count
        db_credential.last_used_at = db.func.now()
        db.session.commit()

        session.pop("webauthn_challenge", None)

        if pending_2fa_user_id:
            # 2FA mode - complete the authentication via the auth route
            return jsonify({"verified": True, "redirect": url_for("auth.complete_2fa")})
        # Usernameless mode - login directly
        from flask_login import login_user

        login_user(admin_account, remember=True)
        return jsonify({"verified": True, "redirect": url_for("admin.dashboard")})

    except Exception:
        return jsonify({"error": "Authentication failed"}), 400


@webauthn_bp.route("/webauthn/credentials", methods=["GET"])
@login_required
def list_credentials():
    """List user's WebAuthn credentials."""
    if not isinstance(current_user, AdminAccount):
        return jsonify({"error": "Only admin accounts can manage passkeys"}), 403

    credentials = WebAuthnCredential.query.filter_by(
        admin_account_id=current_user.id
    ).all()

    return jsonify(
        [
            {
                "id": cred.id,
                "name": cred.name,
                "created_at": cred.created_at.isoformat(),
                "last_used_at": cred.last_used_at.isoformat()
                if cred.last_used_at
                else None,
            }
            for cred in credentials
        ]
    )


@webauthn_bp.route("/webauthn/credentials/<int:credential_id>", methods=["DELETE"])
@login_required
def delete_credential(credential_id):
    """Delete a WebAuthn credential and return updated list."""
    if not isinstance(current_user, AdminAccount):
        return jsonify({"error": "Only admin accounts can manage passkeys"}), 403

    credential = WebAuthnCredential.query.filter_by(
        id=credential_id, admin_account_id=current_user.id
    ).first()

    if not credential:
        return jsonify({"error": "Credential not found"}), 404

    db.session.delete(credential)
    db.session.commit()

    # Return updated passkey list for HTMX
    passkeys = WebAuthnCredential.query.filter_by(
        admin_account_id=current_user.id
    ).all()
    return render_template("components/passkey_list.html", passkeys=passkeys)


# New HTMX-focused endpoints
@webauthn_bp.route("/webauthn/list", methods=["GET"])
@login_required
def list_passkeys_htmx():
    """Return passkey list component for HTMX."""
    if not isinstance(current_user, AdminAccount):
        return render_template("components/passkey_list.html", passkeys=[])

    passkeys = WebAuthnCredential.query.filter_by(
        admin_account_id=current_user.id
    ).all()
    return render_template("components/passkey_list.html", passkeys=passkeys)


@webauthn_bp.route("/webauthn/add-form", methods=["GET"])
@login_required
def show_add_form():
    """Show the add passkey form modal."""
    return render_template("components/passkey_add_form.html")


@webauthn_bp.route("/webauthn/close-modal", methods=["GET"])
@login_required
def close_modal():
    """Close modal by returning empty content."""
    return ""


@webauthn_bp.route("/webauthn/register-start", methods=["POST"])
@login_required
def register_start_htmx():
    """Start WebAuthn registration with HTMX."""
    if not isinstance(current_user, AdminAccount):
        return render_template(
            "components/passkey_error.html",
            error="Only admin accounts can register passkeys",
        )

    name = request.form.get("name", "").strip()
    if not name:
        return render_template(
            "components/passkey_error.html", error="Passkey name is required"
        )

    try:
        try:
            rp_id, rp_name, _ = get_rp_config()
        except ValueError as e:
            return render_template(
                "components/passkey_error.html",
                error=str(e),
            )
        if not rp_id:
            return render_template(
                "components/passkey_error.html",
                error="RP ID is required",
            )

        user_id = str(current_user.id).encode("utf-8")

        existing_credentials = WebAuthnCredential.query.filter_by(
            admin_account_id=current_user.id
        ).all()
        exclude_credentials = [
            PublicKeyCredentialDescriptor(id=cred.credential_id)
            for cred in existing_credentials
        ]

        registration_options = generate_registration_options(
            rp_id=rp_id,
            rp_name=rp_name,
            user_id=user_id,
            user_name=current_user.username,
            user_display_name=current_user.username,
            exclude_credentials=exclude_credentials,
            authenticator_selection=AuthenticatorSelectionCriteria(
                user_verification=UserVerificationRequirement.PREFERRED,
            ),
            supported_pub_key_algs=[
                COSEAlgorithmIdentifier.ECDSA_SHA_256,
                COSEAlgorithmIdentifier.RSASSA_PKCS1_v1_5_SHA_256,
            ],
        )

        session["webauthn_challenge"] = registration_options.challenge
        session["webauthn_user_id"] = user_id
        session["passkey_name"] = name

        # Convert registration options to JSON-serializable format
        def base64url_encode(data):
            return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")

        options_dict = {
            "challenge": base64url_encode(registration_options.challenge),
            "rp": {
                "name": registration_options.rp.name,
                "id": registration_options.rp.id,
            },
            "user": {
                "id": base64url_encode(registration_options.user.id),
                "name": registration_options.user.name,
                "displayName": registration_options.user.display_name,
            },
            "pubKeyCredParams": [
                {"alg": param.alg, "type": param.type}
                for param in registration_options.pub_key_cred_params
            ],
            "timeout": registration_options.timeout,
            "excludeCredentials": [
                {
                    "id": base64url_encode(cred.id),
                    "type": cred.type,
                    "transports": list(cred.transports)
                    if hasattr(cred, "transports") and cred.transports
                    else [],
                }
                for cred in (registration_options.exclude_credentials or [])
            ],
            "authenticatorSelection": {
                "userVerification": registration_options.authenticator_selection.user_verification
                if registration_options.authenticator_selection is not None
                else None
            },
        }

        return render_template(
            "components/passkey_register.html", options=options_dict, name=name
        )

    except Exception:
        return render_template(
            "components/passkey_error.html",
            error="Failed to start passkey registration",
        )
