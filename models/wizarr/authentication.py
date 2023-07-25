from datetime import datetime, timedelta
from logging import info

from flask import request, current_app
from flask_jwt_extended import create_access_token, get_jti
from schematics.exceptions import DataError, ValidationError
from schematics.models import Model
from schematics.types import BooleanType, StringType
from werkzeug.security import check_password_hash, generate_password_hash

from models.database.accounts import Accounts
from models.database.sessions import Sessions


class AuthenticationModel(Model):
    """Authentication Model"""

    # Private Variables
    _user: Accounts | None = None

    # ANCHOR - Authentication Model
    username = StringType(required=True)
    password = StringType(required=True)
    remember = BooleanType(required=False, default=False)

    # ANCHOR - Initialize
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Get the user from the database
        self._get_user()

        # Migrate old passwords if needed
        self._migrate_password()

        # Validate
        self.validate()


    # ANCHOR - Get User
    def _get_user(self) -> Accounts:
        """Get the user from the database

        :return: An admin
        """

        # Get the user from the database
        admin = Accounts.get_or_none(Accounts.username == self.username)

        # Check if the user exists
        if admin is None:
            raise DataError({"username": ["User does not exist"]})

        # Set the user
        self._user = admin


    # ANCHOR - Validate Password
    def validate_password(self, _, value):
        """Validate the password

        :param value: The password
        :type value: str
        """

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
        """Create a jwt token for the user

        :return: A jwt token
        :rtype: str
        """

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
        expiry = datetime.utcnow() + timedelta(days=30) if self.remember else datetime.utcnow() + timedelta(hours=1)

        # Store the admin key in the database
        Sessions.create(session=jti, user=self._user.id, ip=ip_addr, user_agent=user_agent, expires=expiry)

        # Return the token
        return token


    # ANCHOR - Get User
    def get_admin(self) -> Accounts:
        """Get the user from the database

        :return: An admin
        """

        return self._user


class AuthenticationLogoutModel(Model):
    """Authentication Logout Model"""

    # ANCHOR - Authentication Logout Model
    token = StringType(required=False)


    # ANCHOR - Validate Token
    def validate_token(self, _, value):
        """Validate the token

        :param value: The token
        :type value: str
        """

        # Get the session from the database
        session = Sessions.get_or_none(Sessions.session == value)

        # Check if the session exists
        if session is None:
            raise ValidationError("Invalid Token")

        # Set the session
        self._session = session


    # ANCHOR - Get Token
    def get_token(self) -> str:
        """Get the token

        :return: A jwt token
        :rtype: str
        """

        if not current_app:
            raise RuntimeError("Must be called from within a flask route")

        # Get the token
        self.token = request.cookies.get("access_token_cookie", None)

        # Check if the token exists
        if self.token is None:
            raise ValidationError("Invalid Token")

        return self.token


    # ANCHOR - Destroy Session
    def destroy_session(self):
        """Destroy the session"""

        # Get the token
        self.get_token()

        # Get JTI from token
        jti = get_jti(self.token)

        # Delete the session from the database
        session = Sessions.get(Sessions.session == jti)

        # Delete the session
        session.delete_instance()
