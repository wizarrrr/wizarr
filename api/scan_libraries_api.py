from flask import request
from flask_jwt_extended import jwt_required
from flask_restx import Namespace, Resource
from requests import RequestException

from models.libraries import ScanLibraries

api = Namespace(
    "Scan Libraries", description=" related operations", path="/scan-libraries"
)


@api.route("")
class ScanLibrariesListAPI(Resource):
    method_decorators = [jwt_required()]

    @api.doc(description="")
    @api.response(500, "Internal server error")
    def post(self):
        # Import from helpers
        from helpers import scan_jellyfin_libraries, scan_plex_libraries

        # Validate the data and initialize the object
        form = ScanLibraries(
            server_type=request.form.get("server_type", None),
            server_url=request.form.get("server_url", None),
            server_api_key=request.form.get("server_api_key", None),
        )

        # Check if the server type is Jellyfin
        if form.server_type == "jellyfin":
            # Get the libraries
            libraries = scan_jellyfin_libraries(form.server_api_key, form.server_url)

            # Format the libraries as [name]: [id]
            libraries = {library["Name"]: library["Id"] for library in libraries}

            # Return the libraries
            return {"libraries": libraries}, 200

        # Check if the server type is Plex
        if form.server_type == "plex":
            # Get the libraries
            libraries = scan_plex_libraries(form.server_api_key, form.server_url)

            # Format the libraries as [name]: [id]
            libraries = {library.title: library.uuid for library in libraries}

            # Return the libraries
            return {"libraries": libraries}, 200

        raise RequestException("Invalid server type")
