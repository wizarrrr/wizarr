from flask_jwt_extended import current_user
from flask_restx import Namespace, Resource
from playhouse.shortcuts import model_to_dict

from app.utils.software_lifecycle import is_beta, get_current_version, need_update, get_latest_version, get_latest_beta_version
from app.extensions import cache

from json import loads, dumps


api = Namespace("Server", description="Server related operations", path="/server")

@api.route("")
@api.route("/", doc=False)
class Server(Resource):
    """Server related operations"""

    def get(self):
        """Get the details of the server"""
        from app import app
        from app.security import is_setup_required
        from helpers.settings import get_settings
        from helpers.requests import get_requests

        resp = {
            "settings": loads(dumps(get_settings(disallowed=["server_api_key"]),  indent=4, sort_keys=True, default=str)),
            "requests": loads(dumps(get_requests(disallowed=["api_key"]),  indent=4, sort_keys=True, default=str)),
            "version": str(get_current_version()),
            "update_available": need_update(),
            "debug": bool(app.debug),
            "setup_required": is_setup_required(),
            "is_beta": is_beta(),
            "latest_version": str(get_latest_version()),
            "latest_beta_version": str(get_latest_beta_version()),
        }

        return resp, 200
