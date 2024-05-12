from litestar import Router

routes = Router("/plex", tags=["plex"], route_handlers=[])

__all__ = ["routes"]
