from flask import send_file
from flask_jwt_extended import jwt_required, current_user
from flask_restx import Namespace, Resource


api = Namespace("OAuth", description="OAuth related operations", path="/oauth")

@api.route("")
@api.route("/", doc=False)
class OAuth(Resource):
    """OAuth related operations"""

    @api.doc(security="jwt")
    @jwt_required()
    def post(self):
        """Create a new OAuth handler"""
        return { "message": "Hello World!" }, 200