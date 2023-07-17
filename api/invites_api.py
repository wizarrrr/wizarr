
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

api = Namespace('Invites', description='Invites related operations', path="/invites")

@api.route('/')
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
        # Validate the data and initialize the object
        form = InvitationsPostModel(
            code=request.form.get("code", None) or token_hex(3),
            expires=None if not request.form.get("expires", None) or request.form.get("expires", None) != "null" or int(request.form.get("expires")) == 0 else (datetime.now() + timedelta(minutes=int(request.form.get("expires")))),
            unlimited=True if request.form.get("unlimited", None) == "true" else False,
            plex_home=True if request.form.get("plex_home", None) == "true" else False,
            plex_allow_sync=True if request.form.get("plex_allow_sync", None) == "true" else False,
            duration=int(request.form.get("duration")) if request.form.get("duration", None) and request.form.get("duration", None) != "null" else 0,
            libraries=loads(request.form.get("libraries")) if request.form.get("libraries", None) else []
        )
        
        db_libraries = Libraries.select()
        
        # Check if the code is unique
        if Invitations.select().where(Invitations.code == form.code).exists():
            raise InvalidUsage("Code already exists")
        
        # Check if the libraries are valid
        for library in form.libraries:
            if library not in [db_library.id for db_library in db_libraries]:
                raise InvalidUsage("Invalid library name")
            
        # Code must be uppercase
        form.code = form.code.upper()
        
        # If form.library is empty, set it to all libraries
        if len(form.libraries) == 0:
            form.libraries = [db_library.id for db_library in db_libraries]

        
        # Create the invite
        Invitations.create(
            code=form.code,
            expires=form.expires,
            unlimited=form.unlimited,
            duration=form.duration,
            specific_libraries=",".join([str(library) for library in form.libraries]),
            plex_home=form.plex_home,
            plex_allow_sync=form.plex_allow_sync,
            created=datetime.now()
        )
        
        # Create the response
        form.expires = str(form.expires)
        response = form.model_dump()
        
        
        return response, 200