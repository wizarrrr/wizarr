from litestar import Router

routes = Router("/account", tags=["account"], route_handlers=[])

__all__ = ["routes"]
