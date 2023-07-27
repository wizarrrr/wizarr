from playhouse.shortcuts import model_to_dict
from schematics.exceptions import DataError
from flask import jsonify, Response
from logging import info

from models.database.accounts import Accounts
from models.wizarr.authentication import AuthenticationModel
from models.wizarr.accounts import AccountsModel


# INDEX OF FUNCTIONS
# - Login to Account
# - Logout of Account

# ANCHOR - Login to Account
def login_to_account(username: str, password: str, remember: bool = False, response: bool = False) -> Accounts or Response:
    """Login to an account

    :param username: The username of the account
    :type username: str

    :param password: The password of the account
    :type password: str

    :param remember: Whether or not to keep the JWT valid indefinitely
    :type remember: bool

    :param response: Whether or not to return the response instead of the user object
    :type response: bool

    :return: An account
    """

    # Validate the user
    auth = AuthenticationModel({
        "username": username,
        "password": password,
        "remember": remember
    })

    # Get token for user
    token = auth.get_token()

    # Get the admin user
    user = auth.get_admin()

    # If we want to return the response instead of the user object
    if response:

        # Create a response object
        resp = jsonify({
            "message": "Login successful",
            "user": AccountsModel(model_to_dict(user, exclude=[Accounts.password])).to_primitive(),
        })

        # Set the jwt token in the cookie
        auth.set_access_cookies(resp, token)

        # Log message and return response
        info(f"Account {user.username} successfully logged in")

        return resp

    # Return the user object
    return user


# ANCHOR - Logout of Account
def logout_of_account() -> Response:
    """Logout of an account

    :return: A response
    """

    # Create a response object
    response = jsonify({"message": "Successfully logged out"})

    # Delete the jwt token from the cookie
    auth = AuthenticationModel

    # Destroy the session
    auth.destroy_session()

    # Delete the jwt token from the cookie
    auth.unset_access_cookies(response)

    # Log message and return response
    info("Account successfully logged out")
    return response
