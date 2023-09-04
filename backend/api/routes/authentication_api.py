from flask import request
from flask_restx import Namespace, Resource

from app.models.wizarr.authentication import AuthenticationModel
from api.models.authentication import LoginPOST

api = Namespace(name="Authentication", description="Authentication related operations", path="/auth")

api.add_model("LoginPOST", LoginPOST)

@api.route("/login")
@api.route("/login/", doc=False)
class Login(Resource):
    """API resource for logging in"""

    @api.expect(LoginPOST)
    @api.doc(description="Login to the application")
    @api.response(200, "Login successful")
    @api.response(401, "Invalid Username or Password")
    @api.response(500, "Internal server error")
    def post(self):
        """Login to the application"""
        auth = AuthenticationModel(request.form)
        return auth.login_user()

@api.route("/refresh")
@api.route("/refresh/", doc=False)
class Refresh(Resource):
    """API resource for refreshing the JWT token"""

    @api.doc(description="Refresh the JWT token")
    @api.response(200, "Token refreshed")
    @api.response(401, "Invalid refresh token")
    @api.response(500, "Internal server error")
    def post(self):
        """Refresh the JWT token"""
        return AuthenticationModel.refresh_token(request.form.get("refresh_token"))

@api.route("/logout")
@api.route("/logout/", doc=False)
class Logout(Resource):
    """API resource for logging out"""

    @api.doc(description="Logout the currently logged in user")
    @api.response(200, "Logout successful")
    @api.response(500, "Internal server error")
    def get(self):
        """Logout the currently logged in user"""
        return AuthenticationModel.logout_user()
