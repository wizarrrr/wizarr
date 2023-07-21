
from datetime import datetime, timedelta
from json import loads
from logging import info, warning
from random import choices
from string import ascii_uppercase, digits
from typing import Optional

from flask import jsonify, make_response, redirect, request, session
from flask_jwt_extended import jwt_required
from flask_restx import Model, Namespace, Resource, fields
from playhouse.shortcuts import model_to_dict
from pydantic import HttpUrl
from requests import RequestException, get

from app.exceptions import InvalidUsage
from models.libraries import Libraries, LibrariesListPostModel
from models.settings import Settings

api = Namespace('Libraries', description='Libraries related operations', path="/libraries")

@api.route('')
class LibrariesListAPI(Resource):
    
    method_decorators = [jwt_required()]
    
    @api.doc(description="Get all libraries")
    @api.response(500, "Internal server error")
    def get(self):
        # Select all libraries from the database
        libraries = Libraries.select()
        
        # Convert the libraries to a list of dictionaries
        response = [model_to_dict(library, exclude=[Libraries.created]) for library in libraries]
        
        return response, 200
    
    @api.doc(description="")
    @api.response(500, "Internal server error")
    def post(self):
        # Import from helpers
        from helpers import scan_jellyfin_libraries, scan_plex_libraries

        # Validate the data and initialize the object
        form = LibrariesListPostModel(
            libraries=loads(request.form.get("libraries", None))
        )
        
        # Get server_type, server_url, and server_api_key from the database
        settings = {
            settings.key: settings.value
            for settings in Settings.select().where(
                (Settings.key == "server_type") | (Settings.key == "server_url") | (Settings.key == "server_api_key")
            )   
        }
        
        # Place the settings into variables
        server_type = settings["server_type"]
        server_url = HttpUrl(settings["server_url"])
        server_api_key = settings["server_api_key"]
        
        # Store the libraries in a list[dict]
        libraries: Optional[list[dict]] = None
        libraries_dict: Optional[list[dict]] = None
        
        # Check if the server type is Jellyfin
        if server_type == "jellyfin":
            libraries_dict = scan_jellyfin_libraries(server_api_key, server_url)
            libraries = [{"id": library["Id"], "name": library["Name"]} for library in libraries_dict]
            
            
        # Check if the server type is Plex
        if server_type == "plex":
            libraries_dict = scan_plex_libraries(server_api_key, server_url)
            libraries = [{"id": str(library.uuid), "name": library.title} for library in libraries_dict]
        
        # Check if the libraries are None
        if libraries is None:
            raise InvalidUsage("Invalid server type")
        
        # Compare both libraries, if server lib does not contain client lib remove it from libraries
        libraries = [library for library in libraries if library["id"] in form.libraries]
        
        # Delete all libraries in the database that are not in the list of libraries
        deleted = Libraries.delete().where(Libraries.id.not_in([library["id"] for library in libraries])).execute()
        
        info(f"Deleted {deleted} libraries")

        # Loop through pydantic's list of libraries
        for library in libraries:
            # Get the library from the database
            db_library = Libraries.get_or_none(id=library["id"])

            # Create the library and continue to the next library if the library does not exist
            if db_library is None:
                Libraries.create(id=library["id"], name=library["name"])
                info(f"Library {library['name']} created")
                continue
            
            # Update the library name if it is different
            if db_library.name != library["name"]:
                db_library.name = library["name"]
                db_library.save()
                info(f"Library {db_library.name} updated to {library['name']}")
                continue
            
            info(f"Library {library['name']} already exists")
            
        # Create the response
        response = { "message": "Libraries updated", "libraries": libraries }
        
        # Thank god it worked, this took me 2 hours to figure out
        return response, 200