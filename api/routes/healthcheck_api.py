from flask_jwt_extended import current_user
from flask_restx import Namespace, Resource

from psutil import boot_time
from app.utils.software_lifecycle import get_current_version, need_update


api = Namespace("Healthcheck", description="Healthcheck related operations", path="/health")

@api.route("")
@api.route("/", doc=False)
class Healthcheck(Resource):

    def get(self):
        """Get the health of the application"""
        resp = {
            "uptime": str(boot_time()),
            "status": "OK",
            "version": str(get_current_version()),
            "update_available": need_update(),
            "current_user": current_user["username"] if current_user else None
        }

        return resp, 200
