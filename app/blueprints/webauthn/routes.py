import os
import json
import base64
from flask import Blueprint, request, jsonify, current_app, session, url_for, render_template
from flask_login import login_required, current_user
from webauthn import generate_registration_options, verify_registration_response, generate_authentication_options, verify_authentication_response
from webauthn.helpers.structs import AuthenticatorSelectionCriteria, UserVerificationRequirement, AuthenticationCredential
from webauthn.helpers import parse_registration_credential_json, parse_authentication_credential_json
from webauthn.helpers.cose import COSEAlgorithmIdentifier
from app.models import WebAuthnCredential, AdminAccount
from app.extensions import db
webauthn_bp = Blueprint("webauthn", __name__)

def get_rp_config():
    """Get WebAuthn RP configuration based on current request."""
    from flask import request
    from urllib.parse import urlparse
    
    # Default values
    default_rp_name = "Wizarr"
    
    # Check if we have environment overrides
    env_rp_id = os.environ.get("WEBAUTHN_RP_ID")
    env_rp_name = os.environ.get("WEBAUTHN_RP_NAME")
    env_origin = os.environ.get("WEBAUTHN_ORIGIN")
    
    # If environment variables are set, use them
    if env_rp_id and env_rp_name and env_origin:
        current_app.logger.info(f"Using environment WebAuthn config: {env_rp_id}, {env_origin}")
        return env_rp_id, env_rp_name, env_origin
    
    # For HTMX requests, prefer HX-Current-URL header
    current_url = request.headers.get('HX-Current-URL')
    if current_url:
        current_app.logger.info(f"Using HX-Current-URL: {current_url}")
        parsed = urlparse(current_url)
        hostname = parsed.hostname
        origin = f"{parsed.scheme}://{parsed.netloc}"
    else:
        # Fallback to standard request headers
        host = request.headers.get('Host', 'localhost:5000')
        
        # Detect HTTPS from various reverse proxy headers
        is_https = (
            request.is_secure or
            request.headers.get('X-Forwarded-Proto', '').lower() == 'https' or
            request.headers.get('X-Forwarded-Ssl', '').lower() == 'on' or
            request.headers.get('X-Url-Scheme', '').lower() == 'https' or
            request.headers.get('X-Forwarded-Protocol', '').lower() == 'https'
        )
        
        scheme = 'https' if is_https else 'http'
        hostname = host.split(':')[0]
        origin = f"{scheme}://{host}"
        current_app.logger.info(f"Using request headers: Host={host}, scheme={scheme}, is_https={is_https}")
        current_app.logger.info(f"Proxy headers: X-Forwarded-Proto={request.headers.get('X-Forwarded-Proto')}, X-Forwarded-Ssl={request.headers.get('X-Forwarded-Ssl')}")
    
    # WebAuthn RP_ID must match the hostname exactly for proper origin validation
    rp_id = hostname
    
    current_app.logger.info(f"Final WebAuthn config: rp_id={rp_id}, origin={origin}")
    
    return rp_id, default_rp_name, origin


@webauthn_bp.route("/webauthn/debug", methods=["GET", "POST"])
@login_required  
def debug_headers():
    """Debug endpoint to check request headers."""
    from flask import request
    headers_info = {
        'Host': request.headers.get('Host'),
        'HX-Current-URL': request.headers.get('HX-Current-URL'),
        'HX-Request': request.headers.get('HX-Request'),
        'Origin': request.headers.get('Origin'),
        'Referer': request.headers.get('Referer'),
        'User-Agent': request.headers.get('User-Agent'),
        'X-Forwarded-Proto': request.headers.get('X-Forwarded-Proto'),
        'X-Forwarded-Ssl': request.headers.get('X-Forwarded-Ssl'),
        'X-Url-Scheme': request.headers.get('X-Url-Scheme'),
        'X-Forwarded-Protocol': request.headers.get('X-Forwarded-Protocol'),
        'is_secure': request.is_secure,
        'url': request.url,
        'base_url': request.base_url,
        'url_root': request.url_root,
    }
    
    rp_id, rp_name, origin = get_rp_config()
    
    return jsonify({
        'headers': headers_info,
        'webauthn_config': {
            'rp_id': rp_id,
            'rp_name': rp_name,
            'origin': origin
        }
    })



@webauthn_bp.route("/webauthn/register/begin", methods=["POST"])
@login_required
def register_begin():
    """Begin WebAuthn registration process."""
    if not isinstance(current_user, AdminAccount):
        return jsonify({"error": "Only admin accounts can register passkeys"}), 403
    
    rp_id, rp_name, origin = get_rp_config()
    
    user_id = str(current_user.id).encode('utf-8')
    username = current_user.username.encode('utf-8')
    
    existing_credentials = WebAuthnCredential.query.filter_by(admin_account_id=current_user.id).all()
    exclude_credentials = [
        {"id": cred.credential_id, "type": "public-key"}
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
    
    current_app.logger.info(f"Registration completion attempt for user {current_user.username}")
    current_app.logger.info(f"Challenge present: {challenge is not None}")
    current_app.logger.info(f"Expected user ID present: {expected_user_id is not None}")
    current_app.logger.info(f"Passkey name: {passkey_name}")
    
    if not challenge or not expected_user_id:
        return jsonify({"error": "No registration in progress"}), 400
    
    try:
        credential = parse_registration_credential_json(credential_data["credential"])
        
        rp_id, rp_name, origin = get_rp_config()
        
        verification = verify_registration_response(
            credential=credential,
            expected_challenge=challenge,
            expected_origin=origin,
            expected_rp_id=rp_id,
        )
        
        current_app.logger.info(f"Registration verification successful")
        
        # If verify_registration_response() returns without exception, registration is verified
        # Use the name from session, fall back to provided name or default
        credential_name = passkey_name or credential_data.get("name", f"Passkey {len(current_user.webauthn_credentials) + 1}")
        
        new_credential = WebAuthnCredential(
            admin_account_id=current_user.id,
            credential_id=verification.credential_id,
            public_key=verification.credential_public_key,
            sign_count=verification.sign_count,
            name=credential_name
        )
        
        db.session.add(new_credential)
        db.session.commit()
        
        # Clean up session data
        session.pop("webauthn_challenge", None)
        session.pop("webauthn_user_id", None)
        session.pop("passkey_name", None)
        
        current_app.logger.info(f"Successfully registered passkey '{credential_name}' for user {current_user.username}")
        
        return jsonify({
            "verified": True,
            "credential_id": base64.b64encode(verification.credential_id).decode('utf-8'),
            "name": credential_name
        })
            
    except Exception as e:
        current_app.logger.error(f"WebAuthn registration error: {str(e)}", exc_info=True)
        return jsonify({"error": f"Registration failed: {str(e)}"}), 400

@webauthn_bp.route("/webauthn/authenticate/begin", methods=["POST"])
def authenticate_begin():
    """Begin WebAuthn authentication process."""
    username = request.get_json().get("username")
    if not username:
        return jsonify({"error": "Username required"}), 400
    
    rp_id, rp_name, origin = get_rp_config()
    
    admin_account = AdminAccount.query.filter_by(username=username).first()
    if not admin_account:
        return jsonify({"error": "User not found"}), 404
    
    credentials = WebAuthnCredential.query.filter_by(admin_account_id=admin_account.id).all()
    if not credentials:
        return jsonify({"error": "No passkeys registered for this user"}), 404
    
    allow_credentials = [
        {"id": cred.credential_id, "type": "public-key"}
        for cred in credentials
    ]
    
    authentication_options = generate_authentication_options(
        rp_id=rp_id,
        allow_credentials=allow_credentials,
        user_verification=UserVerificationRequirement.PREFERRED,
    )
    
    session["webauthn_challenge"] = authentication_options.challenge
    session["webauthn_username"] = username
    
    return jsonify(authentication_options)

@webauthn_bp.route("/webauthn/authenticate/complete", methods=["POST"])
def authenticate_complete():
    """Complete WebAuthn authentication process."""
    credential_data = request.get_json()
    challenge = session.get("webauthn_challenge")
    username = session.get("webauthn_username")
    
    if not challenge or not username:
        return jsonify({"error": "No authentication in progress"}), 400
    
    admin_account = AdminAccount.query.filter_by(username=username).first()
    if not admin_account:
        return jsonify({"error": "User not found"}), 404
    
    try:
        credential = parse_authentication_credential_json(credential_data["credential"])
        
        db_credential = WebAuthnCredential.query.filter_by(
            credential_id=credential.raw_id,
            admin_account_id=admin_account.id
        ).first()
        
        if not db_credential:
            return jsonify({"error": "Credential not found"}), 404
        
        rp_id, rp_name, origin = get_rp_config()
        
        verification = verify_authentication_response(
            credential=credential,
            expected_challenge=challenge,
            expected_origin=origin,
            expected_rp_id=rp_id,
            credential_public_key=db_credential.public_key,
            credential_current_sign_count=db_credential.sign_count,
        )
        
        # If verify_authentication_response() returns without exception, authentication is verified
        db_credential.sign_count = verification.new_sign_count
        db_credential.last_used_at = db.func.now()
        db.session.commit()
        
        session.pop("webauthn_challenge", None)
        session.pop("webauthn_username", None)
        
        from flask_login import login_user
        login_user(admin_account, remember=True)
        
        return jsonify({
            "verified": True,
            "redirect": url_for("admin.index")
        })
            
    except Exception as e:
        current_app.logger.error(f"WebAuthn authentication error: {str(e)}")
        return jsonify({"error": "Authentication failed"}), 400

@webauthn_bp.route("/webauthn/credentials", methods=["GET"])
@login_required
def list_credentials():
    """List user's WebAuthn credentials."""
    if not isinstance(current_user, AdminAccount):
        return jsonify({"error": "Only admin accounts can manage passkeys"}), 403
    
    credentials = WebAuthnCredential.query.filter_by(admin_account_id=current_user.id).all()
    
    return jsonify([
        {
            "id": cred.id,
            "name": cred.name,
            "created_at": cred.created_at.isoformat(),
            "last_used_at": cred.last_used_at.isoformat() if cred.last_used_at else None
        }
        for cred in credentials
    ])

@webauthn_bp.route("/webauthn/credentials/<int:credential_id>", methods=["DELETE"])
@login_required
def delete_credential(credential_id):
    """Delete a WebAuthn credential and return updated list."""
    if not isinstance(current_user, AdminAccount):
        return jsonify({"error": "Only admin accounts can manage passkeys"}), 403
    
    credential = WebAuthnCredential.query.filter_by(
        id=credential_id,
        admin_account_id=current_user.id
    ).first()
    
    if not credential:
        return jsonify({"error": "Credential not found"}), 404
    
    db.session.delete(credential)
    db.session.commit()
    
    # Return updated passkey list for HTMX
    passkeys = WebAuthnCredential.query.filter_by(admin_account_id=current_user.id).all()
    return render_template("components/passkey_list.html", passkeys=passkeys)


# New HTMX-focused endpoints
@webauthn_bp.route("/webauthn/list", methods=["GET"])
@login_required
def list_passkeys_htmx():
    """Return passkey list component for HTMX."""
    if not isinstance(current_user, AdminAccount):
        return render_template("components/passkey_list.html", passkeys=[])
    
    passkeys = WebAuthnCredential.query.filter_by(admin_account_id=current_user.id).all()
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
        return render_template("components/passkey_error.html", 
                             error="Only admin accounts can register passkeys")
    
    name = request.form.get("name", "").strip()
    if not name:
        return render_template("components/passkey_error.html", 
                             error="Passkey name is required")
    
    try:
        rp_id, rp_name, origin = get_rp_config()
        
        user_id = str(current_user.id).encode('utf-8')
        
        existing_credentials = WebAuthnCredential.query.filter_by(admin_account_id=current_user.id).all()
        exclude_credentials = [
            {"id": cred.credential_id, "type": "public-key"}
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
            return base64.urlsafe_b64encode(data).decode('utf-8').rstrip('=')
        
        current_app.logger.info(f"Creating options_dict with RP ID: {registration_options.rp.id}")
        current_app.logger.info(f"Registration options RP: {registration_options.rp}")
        
        options_dict = {
            "challenge": base64url_encode(registration_options.challenge),
            "rp": {
                "name": registration_options.rp.name,
                "id": registration_options.rp.id
            },
            "user": {
                "id": base64url_encode(registration_options.user.id),
                "name": registration_options.user.name,
                "displayName": registration_options.user.display_name
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
                    "transports": cred.transports
                }
                for cred in (registration_options.exclude_credentials or [])
            ],
            "authenticatorSelection": {
                "userVerification": registration_options.authenticator_selection.user_verification
            }
        }
        
        return render_template("components/passkey_register.html", 
                             options=options_dict, name=name)
        
    except Exception as e:
        current_app.logger.error(f"WebAuthn registration start error: {str(e)}")
        return render_template("components/passkey_error.html", 
                             error="Failed to start passkey registration")