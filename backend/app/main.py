import importlib.metadata

from litestar import Litestar, Request
from litestar.config.cors import CORSConfig
from litestar.datastructures import State
from litestar.openapi import OpenAPIConfig
from litestar.openapi.plugins import ScalarRenderPlugin
from litestar.openapi.spec import Contact, License, Server
from motor import motor_asyncio
from pydantic import BaseModel

from app.controllers import routes
from app.env import SETTINGS


class ScalarRenderPluginRouteFix(ScalarRenderPlugin):
    @staticmethod
    def get_openapi_json_route(request: Request) -> str:
        return f"{SETTINGS.backend_url}/schema/openapi.json"


app = Litestar(
    debug=SETTINGS.debug,
    route_handlers=[routes],
    state=State(
        {
            "mongo": motor_asyncio.AsyncIOMotorClient(
                SETTINGS.mongo.host, SETTINGS.mongo.port
            )[SETTINGS.mongo.collection],
        }
    ),
    openapi_config=OpenAPIConfig(
        title="",
        description="Wizarr is an advanced user invitation and management system for Jellyfin, Plex, Emby etc.",
        version=importlib.metadata.version("wizarr"),
        render_plugins=[ScalarRenderPluginRouteFix()],
        servers=[Server(url=SETTINGS.backend_url, description="Production server.")],
        license=License(
            name="MIT License",
            identifier="MIT",
            url="https://github.com/wizarrrr/wizarr/blob/master/LICENSE.md",
        ),
        contact=Contact(
            name="Wizarr team",
            email="",
            url="https://github.com/wizarrrr/wizarr",
        ),
    ),
    cors_config=CORSConfig(
        allow_origins=[SETTINGS.backend_url],
        allow_credentials=True,
    ),
    type_encoders={BaseModel: lambda m: m.model_dump(by_alias=False)},
)
