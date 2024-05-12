from helpers.services import Service
from litestar import Controller, Router, get, post

from app.state import State


class ServiceController(Controller):
    path = "/{service_id:str}"

    @post("/sync")
    async def sync(self, state: State, service_id: str) -> None:
        await (await Service(state, service_id).get()).sync()

    @post("/scan")
    async def scan(self, state: State, service_id: str) -> None:
        await (await Service(state, service_id).get()).scan()

    @get("/users")
    async def users(self, state: State, service_id: str) -> None:
        await (await Service(state, service_id).get()).users()


routes = Router(
    "/services",
    tags=["services"],
    route_handlers=[ServiceController],
)

__all__ = ["routes"]
