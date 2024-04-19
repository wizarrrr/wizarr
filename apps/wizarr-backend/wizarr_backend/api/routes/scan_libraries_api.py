from flask import request
from flask_jwt_extended import jwt_required
from flask_restx import Namespace, Resource
from requests import RequestException

from app.models.wizarr.libraries import ScanLibrariesModel
from app.security import is_setup_required

api = Namespace(
    "Scan Libraries", description=" related operations", path="/scan-libraries"
)


@api.route("")
class ScanLibrariesListAPI(Resource):
    """Scan Libraries related operations"""

    method_decorators = [] if is_setup_required() else [jwt_required()]

    @api.doc(description="")
    @api.response(500, "Internal server error")
    def get(self):
        # Import from helpers
        from helpers import scan_jellyfin_libraries, scan_plex_libraries, scan_emby_libraries
        from app.models.database import Settings

        # Get the server settings
        settings = {
            setting.key: setting.value
            for setting in Settings.select()
        }

        # Validate the data and initialize the object
        server_settings = ScanLibrariesModel({
            "server_type": settings["server_type"],
            "server_url": settings["server_url"],
            "server_api_key": settings["server_api_key"]
        })

        server_settings.validate()
        server_type, server_url, server_api_key = server_settings.values()


        # Check if the server type is Jellyfin
        if server_type == "jellyfin":
            # Get the libraries
            libraries = scan_jellyfin_libraries(server_api_key, server_url)

            # Format the libraries as [name]: [id]
            libraries = {library["Name"]: library["Id"] for library in libraries}

            # Return the libraries
            return {"libraries": libraries}, 200

        # Check if the server type is Emby
        if server_type == "emby":
            # Get the libraries
            libraries = scan_emby_libraries(server_api_key, server_url)

            # Format the libraries as [name]: [id]
            libraries = {library["Name"]: library["Guid"] for library in libraries}

            # Return the libraries
            return {"libraries": libraries}, 200

        # Check if the server type is Plex
        if server_type == "plex":
            # Get the libraries
            libraries = scan_plex_libraries(server_api_key, server_url)

            # Format the libraries as [name]: [id]
            libraries = {library.title: library.uuid for library in libraries}

            # Return the libraries
            return {"libraries": libraries}, 200

        raise RequestException("Invalid server type")

    @api.doc(description="")
    @api.response(500, "Internal server error")
    def post(self):
        # Import from helpers
        from helpers import scan_jellyfin_libraries, scan_plex_libraries

        # Validate the data and initialize the object
        server_settings = ScanLibrariesModel(request.form)
        server_settings.validate()

        server_type, server_url, server_api_key = server_settings.values()


        # Check if the server type is Jellyfin
        if server_type == "jellyfin":
            # Get the libraries
            libraries = scan_jellyfin_libraries(server_api_key, server_url)

            # Format the libraries as [name]: [id]
            libraries = {library["Name"]: library["Id"] for library in libraries}

            # Return the libraries
            return {"libraries": libraries}, 200

        # Check if the server type is Plex
        if server_type == "plex":
            # Get the libraries
            libraries = scan_plex_libraries(server_api_key, server_url)

            # Format the libraries as [name]: [id]
            libraries = {library.title: library.uuid for library in libraries}

            # Return the libraries
            return {"libraries": libraries}, 200

        raise RequestException("Invalid server type")
