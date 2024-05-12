from litestar import Router

routes = Router("/jellyfin", tags=["jellyfin"], route_handlers=[])

__all__ = ["routes"]
