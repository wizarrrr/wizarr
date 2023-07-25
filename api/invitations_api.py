from flask import request
from flask_restx import Namespace, Resource
from flask_jwt_extended import jwt_required
from playhouse.shortcuts import model_to_dict

from models.database.invitations import Invitations
from models.wizarr.invitations import InvitationsModel

api = Namespace("Invitations", description="Invites related operations", path="/invitations")


@api.route("")
class InvitationsListAPI(Resource):
    """API resource for all invites"""

    method_decorators = [jwt_required()]

    @api.doc(description="Get all invites")
    @api.response(500, "Internal server error")
    def get(self):
        # Select all invites from the database
        invites = Invitations.select()

        # Convert the invites to a list of dictionaries
        response = [
            model_to_dict(invite, exclude=[Invitations.created, Invitations.expires])
            for invite in invites
        ]

        return response, 200

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
