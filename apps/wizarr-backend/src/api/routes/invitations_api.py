from flask import request
from flask_restx import Namespace, Resource
from flask_jwt_extended import jwt_required
from playhouse.shortcuts import model_to_dict
from json import loads, dumps
from datetime import datetime

from app.models.database.invitations import Invitations
from app.models.wizarr.invitations import InvitationsModel

from helpers.webhooks import run_webhook

api = Namespace("Invitations", description="Invites related operations", path="/invitations")


@api.route("")
class InvitationsListAPI(Resource):
    """API resource for all invites"""

    method_decorators = [jwt_required()]

    @api.doc(description="Get all invites")
    @api.response(500, "Internal server error")
    def get(self):
        response = list(Invitations.select().dicts())

        # Convert the specific_libraries and used_by fields to lists
        for invite in response:
            if invite["specific_libraries"] is not None:
                invite["specific_libraries"] = invite["specific_libraries"].split(",")

            if invite["used_by"] is not None:
                invite["used_by"] = invite["used_by"].split(",")

        return loads(dumps(response, indent=4, sort_keys=True, default=str)), 200

    @api.doc(description="Create an invite")
    @api.response(500, "Internal server error")
    def post(self):
        # Initialize the invite
        invite = InvitationsModel(request.form)

        # Validate the invite
        invite.validate()

        # Create the invite
        new_invite = invite.create_invitation()

        # Send the webhook
        run_webhook("invitation_created", new_invite)

        # Create the invite
        return new_invite, 200


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

        # Send the webhook
        run_webhook("invitation_deleted", model_to_dict(invite))

        return {"message": "Invite deleted successfully"}, 200

@api.route("/<string:invite_code>/verify")
class InvitationsVerifyAPI(Resource):
    """API resource for verifying an invite"""

    @api.doc(description="Verify an invite")
    @api.response(404, "Invite not found")
    @api.response(500, "Internal server error")
    def get(self, invite_code):
        # Select the invite from the database
        invitation: Invitations = Invitations.get_or_none(Invitations.code == invite_code)

        if not invitation:
            return {"message": "Invitation not found"}, 404

        if invitation.used is True and invitation.unlimited is not True:
            return {"message": "Invitation has already been used"}, 400

        if invitation.expires and invitation.expires <= datetime.utcnow():
            return {"message": "Invitation has expired"}, 400

        return {"message": "Invitation is valid"}, 200
