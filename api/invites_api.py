
from datetime import datetime, timedelta
from json import dumps, loads
from logging import info, warning
from random import choices
from secrets import token_hex
from string import ascii_uppercase, digits
from typing import Optional

from flask import jsonify, make_response, redirect, request, session
from flask_jwt_extended import jwt_required
from flask_restx import Model, Namespace, Resource, fields
from playhouse.shortcuts import model_to_dict
from pydantic import HttpUrl
from requests import RequestException, get

from app.encoders import DateTimeDecoder
from app.exceptions import InvalidUsage
from models.invitations import Invitations, InvitationsPostModel
from models.libraries import Libraries
from models.wizarr.invitations import InvitationsModel
api = Namespace('Invites', description='Invites related operations', path="/invites")

@api.route('')
class InvitesListAPI(Resource):

    # method_decorators = [jwt_required()]

    @api.doc(description="Get all invites")
    @api.response(500, "Internal server error")
    def get(self):
        # Select all invites from the database
        invites = Invitations.select()

        # Convert the invites to a list of dictionaries
        response = [model_to_dict(invite, exclude=[Invitations.created, Invitations.expires]) for invite in invites]

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
