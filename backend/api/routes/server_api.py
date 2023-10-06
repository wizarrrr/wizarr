from flask_jwt_extended import current_user
from flask_restx import Namespace, Resource
from playhouse.shortcuts import model_to_dict

from app.utils.software_lifecycle import get_current_version, need_update
from app.extensions import cache


api = Namespace("Server", description="Server related operations", path="/server")

@api.route("")
@api.route("/", doc=False)
class Server(Resource):
    """Server related operations"""

    @cache.cached(timeout=3600)
    def get_need_update(self):
        return need_update()

    def get(self):
        """Get the details of the server"""
        from app import app
        from app.security import is_setup_required
        from helpers.settings import get_settings

        resp = {
            "settings": get_settings(disallowed=["server_api_key"]),
            "version": str(get_current_version()),
            "update_available": self.get_need_update(),
            "debug": True if app.debug else False,
            "setup_required": is_setup_required()
        }

        return resp, 200
