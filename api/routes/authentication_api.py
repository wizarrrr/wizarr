from flask import request
from flask_jwt_extended import jwt_required
from flask_restx import Namespace, Resource

from helpers.api import convert_to_form
from helpers.authentication import login_to_account, logout_of_account

from api.models.authentication import LoginPOST


api = Namespace(name="Authentication", description="Authentication related operations", path="/auth")

api.add_model("LoginPOST", LoginPOST)


@api.route("/login")
@api.route("/login/", doc=False)
class Login(Resource):
    """API resource for logging in"""

    method_decorators = [convert_to_form()]

    @api.expect(LoginPOST)
    @api.doc(description="Login to the application")
    @api.response(200, "Login successful")
    @api.response(401, "Invalid Username or Password")
    @api.response(500, "Internal server error")
    def post(self):
        """Login to the application"""
        return login_to_account(**request.form, response=True)


@api.route("/logout")
@api.route("/logout/", doc=False)
class Logout(Resource):
    """API resource for logging out"""

    method_decorators = [jwt_required(optional=True), convert_to_form()]

    @api.doc(description="Logout the currently logged in user")
    @api.response(200, "Logout successful")
    @api.response(500, "Internal server error")
    def post(self):
        """Logout the currently logged in user"""
        return logout_of_account()
