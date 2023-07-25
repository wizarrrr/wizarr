from logging import info

from flask import jsonify, request
from flask_jwt_extended import jwt_required, set_access_cookies, unset_jwt_cookies
from flask_restx import Namespace, Resource
from playhouse.shortcuts import model_to_dict

from models.database.accounts import Accounts
from models.login import LoginPostModel
from models.wizarr.authentication import AuthenticationLogoutModel, AuthenticationModel


api = Namespace(name="Authentication", description="Authentication related operations", path="/auth")

api.add_model("LoginPostModel", LoginPostModel)


@api.route("/login")
class Login(Resource):
    """API resource for logging in"""

    method_decorators = []

    @api.expect(LoginPostModel)
    @api.doc(description="Login to the application")
    @api.response(200, "Login successful")
    @api.response(401, "Invalid Username or Password")
    @api.response(500, "Internal server error")
    def post(self):
        # Validate the user
        auth = AuthenticationModel(request.form)

        # Get token for user
        token = auth.get_token()

        # Get the admin user
        user = auth.get_admin()

        # Create a response object
        response = jsonify(
            {
                "msg": "Login successful",
                "user": model_to_dict(user, exclude=[Accounts.password]),
            }
        )

        # Set the jwt token in the cookie
        set_access_cookies(response, token)

        # Log message and return response
        info(f"User successfully logged in the username {user.username}")
        return response


@api.route("/logout")
class Logout(Resource):
    """API resource for logging out"""

    method_decorators = [jwt_required(optional=True)]

    @api.doc(description="Logout the currently logged in user")
    @api.response(200, "Logout successful")
    @api.response(500, "Internal server error")
    def post(self):
        # Destroy the session
        auth = AuthenticationLogoutModel()
        auth.destroy_session()

        # Create a response object
        response = jsonify({"msg": "Logout successful"})

        # Delete the jwt token from the cookie
        unset_jwt_cookies(response)

        # Log message and return response
        info("User successfully logged out")
        return response
