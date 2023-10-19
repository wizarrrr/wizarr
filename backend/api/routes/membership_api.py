from flask import request
from flask_restx import Namespace, Resource
from flask_jwt_extended import jwt_required, current_user
from playhouse.shortcuts import model_to_dict
from json import loads, dumps

from app.models.database.memberships import Memberships

api = Namespace(name="Membership", description="Membership related operations", path="/membership")

@api.route("/")
@api.route("")
class Membership(Resource):
    """Membership related operations"""

    method_decorators = [jwt_required()]

    @api.doc(description="Get the membership status")
    @api.response(200, "Successfully retrieved the membership status")
    @api.response(500, "Internal server error")
    def get(self):
        """Get the membership status"""
        # Get membership status where user_id is the current user
        response = Memberships.get_or_none(Memberships.user_id == current_user["id"])

        if not response:
            return {"message": "No membership found"}, 404

        return loads(dumps(model_to_dict(response), indent=4, sort_keys=True, default=str)), 200


    @api.doc(description="Set the membership status")
    @api.response(200, "Successfully set the membership status")
    @api.response(500, "Internal server error")
    def post(self):
        """Set the membership status"""
        # Update the membership status if it exists
        if Memberships.get_or_none(user_id=current_user["id"]):
            response = Memberships.get_or_none(user_id=current_user["id"])
            response.token = request.json.get("token")
            response.email = request.json.get("email")
            response.save()
        else:
            response = Memberships.create(user_id=current_user["id"], email=request.json.get("email"), token=request.json.get("token"))

        return loads(dumps(model_to_dict(response), indent=4, sort_keys=True, default=str)), 200


    @api.doc(description="Delete the membership status")
    @api.response(200, "Successfully deleted the membership status")
    @api.response(500, "Internal server error")
    def delete(self):
        """Delete the membership status"""
        # Delete the membership status if it exists
        if Memberships.get_or_none(user_id=current_user["id"]):
            response = Memberships.get_or_none(user_id=current_user["id"])
            response.delete_instance()
        else:
            return {"message": "No membership found"}, 404

        return {"message": "Membership deleted"}, 200
