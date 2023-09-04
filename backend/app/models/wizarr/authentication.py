from datetime import datetime, timedelta
from logging import info

from flask import request, current_app, jsonify
from flask_jwt_extended import create_access_token, create_refresh_token, get_jti, set_access_cookies as set_access_cookies_jwt, unset_access_cookies as unset_access_cookies_jwt

from playhouse.shortcuts import model_to_dict
from werkzeug.security import check_password_hash, generate_password_hash

from schematics.exceptions import DataError, ValidationError
from schematics.models import Model
from schematics.types import BooleanType, StringType

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
            admin = Accounts.get_or_none(Accounts.username == self.username)
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
            Accounts.update(password=new_hash).where(Accounts.username == self._user.username).execute()

            # Log the migration
            info("Migrated password for user: " + self._user.username)


    # ANCHOR - Get ip_address from request
    def _get_ip_address(self):
        return request.headers.get("X-Forwarded-For", request.remote_addr)


    # ANCHOR - Get user_agent from request
    def _get_user_agent(self):
        return request.user_agent.string


    # ANCHOR - Create JWT Token for user
    def get_token(self):
        # Check if the current_app is set
        if not current_app:
            raise RuntimeError("Must be called from within a flask route")

        # Expire length of session
        expire = False if self.remember else None

        # Generate a jwt token
        token = create_access_token(identity=self._user.id, expires_delta=expire)

        # Get JTI from token
        jti = get_jti(token)

        # Get IP address and User Agent from request
        ip_addr = self._get_ip_address()
        user_agent = self._get_user_agent()

        # Create a session expiration
        expiry = datetime.utcnow() + timedelta(days=30) if self.remember else datetime.utcnow() + timedelta(days=1)

        # Store the admin key in the database
        Sessions.create(session=jti, user=self._user.id, ip=ip_addr, user_agent=user_agent, expires=expiry, mfa_id=self._mfa_id)

        # Return the token
        return token

    # ANCHOR - Get JWT Refresh Token for user
    def get_refresh_token(self):
        # Check if the current_app is set
        if not current_app:
            raise RuntimeError("Must be called from within a flask route")

        # Generate a jwt token
        token = create_refresh_token(identity=self._user.id)

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


    # ANCHOR - Get Token from Cookie
    @staticmethod
    def get_token_from_cookie():
        # Check if the current_app is set
        if not current_app:
            raise RuntimeError("Must be called from within a flask route")

        # Get the token
        token = request.cookies.get("access_token_cookie", None)

        # Check if the token exists
        if token is None:
            raise ValidationError("Invalid Token")

        return token


    # ANCHOR - Destroy Session
    @staticmethod
    def destroy_session():
        # Get the token
        token = AuthenticationModel.get_token_from_cookie()

        # Get JTI from token
        jti = get_jti(token)

        # Delete the session from the database
        session: Sessions = Sessions.get(Sessions.session == jti)

        # Delete the session
        session.delete_instance()

    # ANCHOR - Refresh Token
    @staticmethod
    def refresh_token(refresh_token):
        # Check if the current_app is set
        if not current_app:
            raise RuntimeError("Must be called from within a flask route")

        # Exchange the refresh token for a new access token
        access_token = create_access_token(identity=refresh_token, fresh=False)

        # Return the new access token
        return jsonify({"token": access_token})


    # ANCHOR - Login User
    def login_user(self):
        # Get Tokens and User
        token = self.get_token()
        refresh_token = self.get_refresh_token()

        # Create a response object
        resp = jsonify({
            "message": "Login successful",
            "auth": {
                "user": AccountsModel(model_to_dict(self._user, exclude=[Accounts.password])).to_primitive(),
                "token": token,
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
        response = jsonify({"message": "Successfully logged out"})

        # Delete the jwt token from the cookie
        auth = AuthenticationModel

        # Destroy the session
        auth.destroy_session()

        info("Successfully logged out")
        return response
