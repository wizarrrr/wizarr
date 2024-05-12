from litestar import Router

from app.controllers.services import emby, jellyfin, plex

routes = Router(
    "/services",
    tags=["services"],
    route_handlers=[emby.routes, jellyfin.routes, plex.routes],
)

__all__ = ["routes"]
