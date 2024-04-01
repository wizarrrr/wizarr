from base64 import urlsafe_b64decode, urlsafe_b64encode
from logging import info
from secrets import token_hex
from json import loads, dumps

from flask import jsonify, make_response, request, session
from flask_jwt_extended import current_user, jwt_required
from flask_restx import Namespace, Resource
from playhouse.shortcuts import model_to_dict

from webauthn import generate_authentication_options
from webauthn import generate_registration_options
from webauthn import options_to_json
from webauthn import verify_authentication_response
from webauthn import verify_registration_response

from webauthn.helpers.structs import AuthenticationCredential
from webauthn.helpers.structs import AuthenticatorSelectionCriteria
from webauthn.helpers.structs import COSEAlgorithmIdentifier
from webauthn.helpers.structs import PublicKeyCredentialCreationOptions
from webauthn.helpers.structs import PublicKeyCredentialRequestOptions
from webauthn.helpers.structs import RegistrationCredential
from webauthn.helpers.structs import UserVerificationRequirement

from app.models.database.accounts import Accounts
from app.models.database.sessions import Sessions
from app.models.database.mfa import MFA
from app.models.wizarr.accounts import AccountsModel
from app.models.wizarr.authentication import AuthenticationModel

api = Namespace("MFA", description="MFA related operations", path="/mfa")


@api.route("")
@api.route("/", doc=False)
class MFAListAPI(Resource):
    """
    Get all MFA devices
    """

    @jwt_required()
    def get(self):

        # Check if there is a current user
        if not current_user:
            return {"message": "No user found"}, 401

        response = list(MFA.select().where(MFA.user_id == current_user["id"]).dicts())
        return loads(dumps(response, indent=4, sort_keys=True, default=str)), 200


@api.route("/<int:mfa_id>")
class MFAAPI(Resource):
    """
    Manage a specific MFA device
    """

    @jwt_required()
    def get(self, mfa_id: int):
        """
        Get a specific MFA device
        """

        # Check if there is a current user
        if not current_user:
            return {"message": "No user found"}, 401

        # Get the MFA
        mfa: MFA = MFA.get_or_none(MFA.id == mfa_id)

        # Check if the MFA exists
        if not mfa:
            return {"message": "MFA not found"}, 404

        # Check if the MFA belongs to the current user
        if int(mfa.user_id) != int(current_user["id"]):
            return {"message": "MFA not found"}, 404

        # Return the response
        return jsonify(model_to_dict(mfa)), 200


    @jwt_required()
    def put(self, mfa_id: int):
        """
        Update a specific MFA device
        """

        # Check if there is a current user
        if not current_user:
            return {"message": "No user found"}, 401

        # Get the MFA
        mfa: MFA = MFA.get_or_none(MFA.id == mfa_id)

        # Check if the MFA exists
        if not mfa:
            return {"message": "MFA not found"}, 404

        # Check if the MFA belongs to the current user
        if int(mfa.user_id) != int(current_user["id"]):
            return {"message": "MFA not found"}, 404

        # Get the request data
        data = request.get_json()

        # Check if the request data is valid
        if not data:
            return {"message": "Invalid request data"}, 400

        # Check if the request data has the required fields
        if "name" not in data:
            return {"message": "Invalid request data"}, 400

        # Update the MFA
        mfa.name = data["name"]
        mfa.save()

        # Return the response
        return {"message": "MFA name updated"}, 200


    @jwt_required()
    def delete(self, mfa_id: int):
        """
        Delete a specific MFA device
        """

        # Check if there is a current user
        if not current_user:
            return {"message": "No user found"}, 401

        # Get the MFA and MFA session
        mfa: MFA = MFA.get_or_none(MFA.id == mfa_id)
        mfa_session: Sessions = Sessions.get_or_none(Sessions.mfa_id == mfa.id)

        # Check if the MFA exists
        if not mfa:
            return {"message": "MFA not found"}, 404

        # Check if the MFA belongs to the current user
        if int(mfa.user_id) != int(current_user["id"]):
            return {"message": "MFA not found"}, 404

        # Check if the MFA session exists
        if mfa_session:
            # Delete the MFA session
            mfa_session.delete_instance()

        # Delete the MFA
        mfa.delete_instance()

        # Return the response
        return {"message": "MFA deleted"}, 200


@api.route("/registration")
class MFARegisterAPI(Resource):
    """
    Register a new MFA device
    """

    @jwt_required()
    @api.doc(body=False)
    def get(self):
        """
        Register a new MFA device
        """

        # Check if there is a current user
        if not current_user:
            return {"message": "No user found"}, 401

        # Get host and protocol forwarded from nginx
        host = request.headers.get("X-Forwarded-Host", request.host)

        # Remove port from host if it exists
        if ":" in host:
            host = host.split(":")[0]

        # Get the MFAs for the current user
        user_mfas: list[MFA] = MFA.select().where(MFA.user_id == current_user["id"])

        # Create the registration variables
        rp_id = host
        rp_name = "Wizarr"
        user_id = str(current_user["id"])
        user_name = str(current_user["username"])

        authenticator_selection = AuthenticatorSelectionCriteria(
            user_verification = UserVerificationRequirement.REQUIRED
        )

        supported_pub_key_algs = [
            COSEAlgorithmIdentifier.ECDSA_SHA_256,
            COSEAlgorithmIdentifier.RSASSA_PKCS1_v1_5_SHA_256,
        ]

        exclude_credentials = [
            { "id": urlsafe_b64decode(cred.credential_id), "transports": cred.transports.split(","), "type": "public-key" }
            for cred in user_mfas
        ]

        # Generate the registration options
        registration_options = generate_registration_options(
            rp_id = rp_id,
            rp_name = rp_name,
            user_id = user_id,
            user_name = user_name,
            authenticator_selection = authenticator_selection,
            supported_pub_key_algs = supported_pub_key_algs,
            exclude_credentials = exclude_credentials
        )

        # Store the options in the session
        session["registration_options"] = registration_options

        # Return the response
        response = make_response(options_to_json(registration_options), 200)
        response.headers["Content-Type"] = "application/json"
        return response


    @jwt_required()
    def post(self):
        """
        Verify the MFA registration
        """

        # Check if there is a current user
        if not current_user:
            return {"message": "No user found"}, 401

        # Get the registration options from the session
        registration_options: PublicKeyCredentialCreationOptions = session.get("registration_options", None)

        # Check if the registration options are valid
        if not registration_options:
            return {"message": "No registration options found"}, 400


        # Get the registration response
        registration = request.get_json()

        credential = registration.get("registration")
        name = registration.get("name", None)
        transports = loads(credential).get("response", "{}").get("transports", "[]")

        # Check if the registration response is valid
        if not registration.get("registration", None):
            return {"message": "No registration found"}, 400

        if not registration.get("origin", None):
            return {"message": "No origin found"}, 400


        # Verify the registration response
        verified_credential = verify_registration_response(
            credential=RegistrationCredential.parse_raw(credential),
            expected_challenge=registration_options.challenge,
            expected_rp_id = registration_options.rp.id,
            expected_origin = registration.get("origin")
        )

        # Get the credential ID and public key
        credential_id = urlsafe_b64encode(verified_credential.credential_id)
        public_key = urlsafe_b64encode(verified_credential.credential_public_key)
        sign_count = verified_credential.sign_count
        attestation = urlsafe_b64encode(verified_credential.attestation_object)

        # Add the credential to the users MFA credentials
        mfa_id = MFA.create(
            name = name if name else "MFA Device: " + token_hex(6),
            user_id = current_user["id"],
            aaguid = verified_credential.aaguid,
            credential_id = credential_id,
            public_key = public_key,
            sign_count = sign_count,
            attestation = attestation,
            transports = ",".join(transports)
        )

        # Get the MFA details
        mfa = model_to_dict(MFA.get_or_none(MFA.id == mfa_id))
        return loads(dumps(mfa, indent=4, sort_keys=True, default=str)), 200


@api.route("/authentication")
class MFAAuthenticateAPI(Resource):
    """
    Authenticate with an MFA device
    """

    @api.doc(body=False)
    def get(self):
        """
        Authenticate with an MFA device
        """

        # Get host and protocol
        host = request.headers.get("X-Forwarded-Host", request.host)

        # Remove port from host if it exists
        if ":" in host:
            host = host.split(":")[0]

        # Create the authentication variables
        rp_id = host

        # Get the username from the request
        username = request.args.get("username", None)
        allow_credentials = None

        # If the username is provided, allow only the credentials for that user
        if username:

            # Get the user from the database
            user = Accounts.get_or_none(Accounts.username == username)

            # Check if the user exists
            if not user:
                return {"message": "User not found"}, 404

            # Get the MFAs for the current user
            user_mfas: list[MFA] = MFA.select().where(MFA.user_id == user.id)

            allow_credentials = [
                { "id": urlsafe_b64decode(cred.credential_id), "transports": cred.transports.split(","), "type": "public-key" }
                for cred in user_mfas
            ]


        # Generate the authentication options
        authentication_options = generate_authentication_options(
            rp_id = rp_id,
            user_verification = UserVerificationRequirement.REQUIRED,
            allow_credentials = allow_credentials
        )

        # Store the options in the session
        session["authentication_options"] = authentication_options

        # Return the response
        response = make_response(options_to_json(authentication_options), 200)
        response.headers["Content-Type"] = "application/json"
        return response


    def post(self):
        """
        Verify the MFA authentication
        """

        # Get host and protocol
        host = request.headers.get("X-Forwarded-Host", request.host)

        # Remove port from host if it exists
        if ":" in host:
            host = host.split(":")[0]

        # Create the authentication variables
        rp_id = host

        # Get the authentication response
        authentication = request.get_json()

        # Check if the authentication response is valid
        if not authentication.get("assertion", None) or not authentication.get("origin", None):
            return {"message": "Invalid authentication response"}, 400

        # Get the variables from the authentication response
        assertion = AuthenticationCredential.parse_raw(authentication.get("assertion", None))
        origin = authentication.get("origin", None)

        # Get the MFA credentials for the user based on credential ID
        mfa_credentials: MFA = MFA.get_or_none(MFA.credential_id == urlsafe_b64encode(assertion.raw_id))

        # Check if the user has any MFA credentials
        if not mfa_credentials:
            return {"message": "MFA not found"}, 404


        # Get the authentication options from the session
        authentication_options: PublicKeyCredentialRequestOptions = session.get("authentication_options", None)

        # Check if the authentication options are valid
        if not authentication_options:
            return {"message": "No authentication options found"}, 400

        # Get variables from the mfa credentials
        public_key = urlsafe_b64decode(mfa_credentials.public_key)
        sign_count = mfa_credentials.sign_count

        # Verify the authentication response
        verified_credential = verify_authentication_response(
            credential=assertion,
            expected_challenge=authentication_options.challenge,
            expected_rp_id=rp_id,
            expected_origin=origin,
            credential_public_key=public_key,
            credential_current_sign_count=sign_count,
            require_user_verification=True
        )

        # Update the sign count
        mfa_credentials.sign_count = verified_credential.new_sign_count
        mfa_credentials.save()

        # Log the user in
        auth = AuthenticationModel({}, mfa=True, user_id=mfa_credentials.user_id, mfa_id=mfa_credentials.id)

        # Get token for user
        access_token = auth.get_access_token()
        refresh_token = auth.get_refresh_token(access_token)

        # Get the admin user
        user = auth.get_admin()

         # Create a response object
        resp = jsonify({
            "message": "Successfully authenticated with MFA device",
            "auth": {
                "token": access_token,
                "refresh_token": refresh_token,
                "user": loads(dumps(model_to_dict(user, exclude=[Accounts.password]), indent=4, sort_keys=True, default=str)),
            }
        })

        # Log message and return response
        info(f"Account {user.username} successfully logged in")

        return resp


    @api.route("/available")
    class MFAAvailableAPI(Resource):
        """
        Check if MFA is available for specific user
        """

        def post(self):
            """
            Check if MFA is available for specific user
            """

            # Get username from request body
            username = request.get_json()["username"]

            # Check if the username is valid
            if not username:
                return {"message": "No username found"}, 400

            # Get the user from the database
            user = Accounts.get_or_none(Accounts.username == username.lower())

            # Check if the user exists
            if not user:
                return {"message": "User does not exist"}, 404

            # Get the MFA credentials for the user
            mfa_credentials: MFA = MFA.select().where(MFA.user_id == user.id)

            # Count the number of MFA credentials
            mfa_credentials_count = mfa_credentials.count()

            # Return the response
            return {"mfa_available": mfa_credentials_count > 0}, 200
