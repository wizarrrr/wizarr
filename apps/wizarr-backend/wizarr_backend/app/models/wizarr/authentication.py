from datetime import datetime, timedelta
from logging import info

from flask import current_app, jsonify, request
from flask_jwt_extended import (create_access_token, create_refresh_token,
                                decode_token, get_jti, get_jwt,
                                get_jwt_identity)
from flask_jwt_extended import set_access_cookies as set_access_cookies_jwt
from flask_jwt_extended import unset_access_cookies as unset_access_cookies_jwt
from flask_jwt_extended import verify_jwt_in_request
from playhouse.shortcuts import model_to_dict
from schematics.exceptions import DataError, ValidationError
from schematics.models import Model
from schematics.types import BooleanType, StringType
from werkzeug.security import check_password_hash, generate_password_hash
from json import loads, dumps

from app.models.database.accounts import Accounts
from app.models.database.sessions import Sessions
from app.models.wizarr.accounts import AccountsModel


class AuthenticationModel(Model):
    """Authentication Model"""

    # Private Variables
    _user: Accounts | None = None
    _mfa: bool = False
    _user_id: int | None = None
    _mfa_id: str | None = None


    # ANCHOR - Authentication Model
    username = StringType(required=True)
    password = StringType(required=True)
    remember = BooleanType(required=False, default=True)


    # ANCHOR - Initialize
    def __init__(self, *args, **kwargs):
        # Get the mfa value from the kwargs and remove it
        mfa = kwargs.get("mfa", False)
        kwargs.pop("mfa", None)

        # Set the mfa value to the class
        self._mfa = mfa

        # Get the user_id value from the kwargs and remove it
        self._user_id = kwargs.get("user_id", None)
        kwargs.pop("user_id", None)

        # Get the mfa_id value from the kwargs and remove it
        self._mfa_id = kwargs.get("mfa_id", None)
        kwargs.pop("mfa_id", None)

        super().__init__(*args, **kwargs)

        # Get the user from the database
        self._get_user()

        # Skip the rest if mfa is passed
        if (mfa): return

        # Migrate old passwords if needed
        self._migrate_password()

        # Validate unless partial is set
        self.validate()


    # ANCHOR - Get User
    def _get_user(self) -> Accounts:
        # Create admin variable
        admin: Accounts | None = None

        # Get the user from the database
        if not self._mfa and self.username:
            admin = Accounts.get_or_none(Accounts.username == self.username.lower())
        elif self._mfa and self._user_id:
            admin = Accounts.get_or_none(Accounts.id == self._user_id)

        # Check if the user exists
        if admin is None:
            raise DataError({"username": ["User does not exist"]})

        # Set the user
        self._user = admin


    # ANCHOR - Validate Password
    def validate_password(self, _, value):
        # Check if the password is correct
        if not check_password_hash(self._user.password, value):
            raise ValidationError("Invalid Username or Password")

    # ANCHOR - Perform migration of old passwords
    def _migrate_password(self):
        # Migrate to scrypt from sha 256
        if self._user.password.startswith("sha256"):
            # Generate the new hash
            new_hash = generate_password_hash(self.password, method='scrypt')

            # Update the password in the database
            Accounts.update(password=new_hash).where(Accounts.username == self._user.username.lower()).execute()

            # Log the migration
            info("Migrated password for user: " + self._user.username)


    # ANCHOR - Get ip_address from request
    def _get_ip_address(self):
        return request.headers.get("X-Forwarded-For", request.remote_addr)


    # ANCHOR - Get user_agent from request
    def _get_user_agent(self):
        return request.user_agent.string


    # ANCHOR - Create JWT Token for user
    def get_access_token(self):
        # Check if the current_app is set
        if not current_app:
            raise RuntimeError("Must be called from within a flask route")

        # Generate a jwt token
        token = create_access_token(identity=self._user.id, fresh=True)

        # Get JTI from token
        jti = get_jti(token)

        # Decode the token to get the expiry
        expiry = datetime.fromtimestamp(decode_token(token)["exp"])

        # Get IP address and User Agent from request
        ip_addr = self._get_ip_address()
        user_agent = self._get_user_agent()

        # Store the admin key in the database
        Sessions.create(access_jti=jti, user=self._user.id, ip=ip_addr, user_agent=user_agent, expires=expiry, mfa_id=self._mfa_id, created=datetime.utcnow())

        # Return the token
        return token

    # ANCHOR - Get JWT Refresh Token for user
    def get_refresh_token(self, access_token: str = None):
        # Check if the current_app is set
        if not current_app:
            raise RuntimeError("Must be called from within a flask route")

        # Generate a jwt token
        token = create_refresh_token(identity=self._user.id)

        # Update the session with the refresh token
        if access_token is not None:
            session = Sessions.get(Sessions.access_jti == get_jti(access_token))
            session.refresh_jti = get_jti(token)
            session.save()

        # Return the token
        return token

    # ANCHOR - Set access cookies
    @staticmethod
    def set_access_cookies(response, token):
        return set_access_cookies_jwt(response, token)


    # ANCHOR - Unset access cookies
    @staticmethod
    def unset_access_cookies(response):
        return unset_access_cookies_jwt(response)


    # ANCHOR - Get User
    def get_admin(self) -> Accounts:
        # Return the user object
        return self._user


    # ANCHOR - Destroy Session
    @staticmethod
    def destroy_session():
        # Get the token
        token = get_jwt()
        jti = token["jti"]

        # Delete the session from the database
        session = Sessions.get_or_none((Sessions.access_jti == jti) | (Sessions.refresh_jti == jti))

        # Delete the session
        session.delete_instance()

    # ANCHOR - Refresh Token
    # @staticmethod
    # def refresh_token():
    #     # Check if the current_app is set
    #     if not current_app:
    #         raise RuntimeError("Must be called from within a flask route")

    #     # Get the identity of the user
    #     identity = get_jwt_identity()
    #     jti = get_jwt()["jti"]

    #     # Find the session in the database where the access_jti or refresh_jti matches the jti
    #     session = Sessions.get_or_none((Sessions.access_jti == jti) | (Sessions.refresh_jti == jti))

    #     # Exchange the refresh token for a new access token
    #     access_token = create_access_token(identity=identity)

    #     # Update the access token in the database
    #     session.access_jti = get_jti(access_token)
    #     session.save()

    #     # Return the new access token
    #     return jsonify(access_token=access_token)


    # ANCHOR - Login User
    def login_user(self):
        # Get Tokens and User
        access_token = self.get_access_token()
        refresh_token = self.get_refresh_token(access_token)

        # Create a response object
        resp = jsonify({
            "message": "Login successful",
            "auth": {
                "user": loads(dumps(model_to_dict(self._user, exclude=[Accounts.password]), indent=4, sort_keys=True, default=str)),
                "token": access_token,
                "refresh_token": refresh_token
            }
        })

        # Log message and return response
        info(f"Account {self._user.username} successfully logged in")
        return resp

    # ANCHOR - Logout User
    @staticmethod
    def logout_user():
        # Create a response object
        response = jsonify({ "message": "Successfully logged out" })

        # Delete the jwt token from the cookie
        auth = AuthenticationModel

        # Destroy the session
        auth.destroy_session()

        info("Successfully logged out")
        return response
