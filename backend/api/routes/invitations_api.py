from flask import request
from flask_restx import Namespace, Resource
from flask_jwt_extended import jwt_required
from playhouse.shortcuts import model_to_dict
from json import loads, dumps

from app.models.database.invitations import Invitations
from app.models.wizarr.invitations import InvitationsModel

api = Namespace("Invitations", description="Invites related operations", path="/invitations")


@api.route("")
class InvitationsListAPI(Resource):
    """API resource for all invites"""

    method_decorators = [jwt_required()]

    @api.doc(description="Get all invites")
    @api.response(500, "Internal server error")
    def get(self):
        response = list(Invitations.select().dicts())
        return loads(dumps(response, indent=4, sort_keys=True, default=str)), 200

    @api.doc(description="Create an invite")
    @api.response(500, "Internal server error")
    def post(self):
        # Initialize the invite
        invite = InvitationsModel(request.form)

        # Validate the invite
        invite.validate()

        # Create the invite
        invite.create_invitation()

        return invite.to_primitive(), 200


@api.route("/<int:invite_id>")
class InvitationsAPI(Resource):
    """API resource for a single invite"""

    method_decorators = [jwt_required()]

    @api.doc(description="Get a single invite")
    @api.response(404, "Invite not found")
    @api.response(500, "Internal server error")
    def get(self, invite_id):
        # Select the invite from the database
        invite = Invitations.get_or_none(Invitations.id == invite_id)

        # Check if the invite exists
        if not invite:
            return {"message": "Invite not found"}, 404

        return model_to_dict(invite, exclude=[Invitations.created, Invitations.expires]), 200

    @api.doc(description="Delete a single invite")
    @api.response(404, "Invite not found")
    @api.response(500, "Internal server error")
    def delete(self, invite_id):
        # Select the invite from the database
        invite = Invitations.get_or_none(Invitations.id == invite_id)

        # Check if the invite exists
        if not invite:
            return {"message": "Invite not found"}, 404

        # Delete the invite
        invite.delete_instance()

        return {"message": "Invite deleted successfully"}, 200
