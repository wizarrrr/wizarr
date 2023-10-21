from flask_jwt_extended import current_user
from flask_restx import Namespace, Resource

from psutil import boot_time
from app.utils.software_lifecycle import get_current_version, need_update
from app.extensions import cache


api = Namespace("Healthcheck", description="Healthcheck related operations", path="/health")

@api.route("")
@api.route("/", doc=False)
class Healthcheck(Resource):
    """Healthcheck related operations"""

    @cache.cached(timeout=3600)
    def get_need_update(self):
        return need_update()

    def get(self):
        """Get the health of the application"""
        from app import app
        from app.security import is_setup_required

        resp = {
            "uptime": str(boot_time()),
            "status": "OK",
            "version": str(get_current_version()),
            "update_available": self.get_need_update(),
            "debug": True if app.debug else False
        }

        return resp, 200
