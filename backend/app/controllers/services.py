from litestar import Controller, Router, get, post

from app.helpers.services import Service
from app.state import State


class ServiceController(Controller):
    path = "/{service_id:str}"


routes = Router(
    "/services",
    tags=["services"],
    route_handlers=[ServiceController],
)

__all__ = ["routes"]
