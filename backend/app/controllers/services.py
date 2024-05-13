from litestar import Controller, Router, delete, get, patch, post
from models.services.base import (
    CreateServiceApiModel,
    ServiceApiFilter,
    ServiceApiModel,
    ServiceApiUpdateModel,
)

from app.helpers.services import Service, create_service, services
from app.state import State


class ServiceController(Controller):
    path = "/{service_id:str}"

    @get("/")
    async def get_service(self, state: State, service_id: str) -> ServiceApiModel:
        return (await Service(state, service_id).get()).details

    @delete("/")
    async def delete_service(self, state: State, service_id: str) -> None:
        await Service(state, service_id).delete()

    @patch("/")
    async def update_service(
        self, state: State, update: ServiceApiUpdateModel, service_id: str
    ) -> None:
        await Service(state, service_id).update(update)


@post("/")
async def post_create_service(
    state: State, data: CreateServiceApiModel
) -> ServiceApiModel:
    return (await create_service(state, data)).details


@get("/")
async def list_services(
    state: State, data: ServiceApiFilter | None = None
) -> list[ServiceApiModel]:
    return await services(state, data)


routes = Router(
    "/services",
    tags=["services"],
    route_handlers=[ServiceController, list_services],
)

__all__ = ["routes"]
