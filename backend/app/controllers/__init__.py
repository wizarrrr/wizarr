from litestar import Router

from app.controllers import account, invites, services

routes = Router(
    "/api/v5",
    route_handlers=[services.routes, services.routes, account.routes, invites.routes],
)

__all__ = ["routes"]
