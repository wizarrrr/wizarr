from typing import Literal

from pydantic import BaseModel, Field, HttpUrl

from app.const import SERVICE_TYPES


class CreateServiceApiModel(BaseModel):
    alias: str | None = Field(None, max_length=64)
    type: SERVICE_TYPES
    key: str = Field(max_length=128)
    url: HttpUrl


class ServiceApiModel(CreateServiceApiModel):
    id: str = Field(alias="_id", description="Unique ID for service", min_length=3)


class ServiceApiUpdateModel(BaseModel):
    type: SERVICE_TYPES | None = None
    alias: str | None = None
    key: str | None = None
    url: str | None = None
