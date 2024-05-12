from litestar import Router

routes = Router("/invites", tags=["invites"], route_handlers=[])

__all__ = ["routes"]
