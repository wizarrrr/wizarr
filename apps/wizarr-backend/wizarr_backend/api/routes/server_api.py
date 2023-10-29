from flask_jwt_extended import current_user
from flask_restx import Namespace, Resource
from playhouse.shortcuts import model_to_dict

from app.utils.software_lifecycle import get_current_version, need_update, get_latest_version, get_latest_beta_version
from app.extensions import cache


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
            "settings": get_settings(disallowed=["server_api_key"]),
            "requests": get_requests(disallowed=["api_key"]),
            "version": str(get_current_version()),
            "update_available": need_update(),
            "debug": True if app.debug else False,
            "setup_required": is_setup_required(),
            "latest_version": str(get_latest_version()),
            "latest_beta_version": str(get_latest_beta_version()),
        }

        return resp, 200
