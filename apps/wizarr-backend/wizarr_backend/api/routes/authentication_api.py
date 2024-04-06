from flask import request
from flask_restx import Namespace, Resource

from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models.wizarr.authentication import AuthenticationModel
from api.models.authentication import LoginPOST

from app.models.database.sessions import Sessions
from flask import current_app, jsonify
from flask_jwt_extended import create_access_token, get_jti, get_jwt

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

    method_decorators = [jwt_required(refresh=True)]

    @api.doc(description="Refresh the JWT token")
    @api.response(200, "Token refreshed")
    @api.response(401, "Invalid refresh token")
    @api.response(500, "Internal server error")
    def post(self):
        """Refresh the JWT token"""
        # Check if the current_app is set
        if not current_app:
            raise RuntimeError("Must be called from within a flask route")

        # Get the identity of the user
        identity = get_jwt_identity()
        jti = get_jwt()["jti"]

        # Find the session in the database where the access_jti or refresh_jti matches the jti
        session = Sessions.get_or_none((Sessions.access_jti == jti) | (Sessions.refresh_jti == jti))

        # Exchange the refresh token for a new access token
        access_token = create_access_token(identity=identity)

        # Update the access token in the database
        session.access_jti = get_jti(access_token)
        session.save()

        # Return the new access token
        return jsonify(access_token=access_token)

@api.route("/logout")
@api.route("/logout/", doc=False)
class Logout(Resource):
    """API resource for logging out"""

    method_decorators = [jwt_required()]

    @api.doc(description="Logout the currently logged in user")
    @api.response(200, "Logout successful")
    @api.response(500, "Internal server error")
    def post(self):
        """Logout the currently logged in user"""
        return AuthenticationModel.logout_user()