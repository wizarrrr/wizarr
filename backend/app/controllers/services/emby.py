from litestar import Router

routes = Router("/emby", tags=["emby"], route_handlers=[])

__all__ = ["routes"]
