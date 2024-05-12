import importlib.metadata
from typing import Any, Optional

from aiohttp import ClientSession
from litestar import Litestar, Request
from litestar.config.cors import CORSConfig
from litestar.connection import ASGIConnection
from litestar.datastructures import State
from litestar.openapi import OpenAPIConfig
from litestar.openapi.plugins import ScalarRenderPlugin
from litestar.openapi.spec import Contact, License, Server
from litestar.security.jwt import JWTCookieAuth, Token
from motor import motor_asyncio
from pydantic import BaseModel

from app.controllers import routes
from app.env import SETTINGS
from app.models.account import AccountModel


async def retrieve_account_handler(
    token: "Token", connection: ASGIConnection[Any, Any, Any, Any]
) -> Optional[AccountModel]:
    pass


class ScalarRenderPluginRouteFix(ScalarRenderPlugin):
    @staticmethod
    def get_openapi_json_route(request: Request) -> str:
        return f"{SETTINGS.backend_url}/schema/openapi.json"


async def start_aiohttp(app: Litestar) -> None:
    if not hasattr(app.state, "aiohttp"):
        app.state.aiohttp = ClientSession()


async def close_aiohttp(app: Litestar) -> None:
    if hasattr(app.state, "aiohttp"):
        await app.state.aiohttp.close()


app = Litestar(
    debug=SETTINGS.debug,
    route_handlers=[routes],
    on_startup=[start_aiohttp],
    on_shutdown=[close_aiohttp],
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
        allow_origins=[SETTINGS.backend_url, SETTINGS.frontend_url],
        allow_methods=["OPTIONS", "GET", "DELETE", "POST", "PATCH"],
        allow_credentials=True,
        allow_headers=["Authorization", "Content-type"],
    ),
    on_app_init=[
        JWTCookieAuth[AccountModel](
            retrieve_user_handler=retrieve_account_handler,
            token_secret=SETTINGS.jwt_token,
            exclude=["/login", "/schema"],
            exclude_opt_key="exclude_auth",
        ).on_app_init
    ],
    type_encoders={BaseModel: lambda m: m.model_dump(by_alias=False)},
)
