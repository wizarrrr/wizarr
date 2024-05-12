from pydantic import BaseModel
from pydantic_settings import BaseSettings


class MongoDB(BaseModel):
    host: str = "localhost"
    port: int = 27017
    collection: str = "wizarr_v5"


class Settings(BaseSettings):
    mongo: MongoDB = MongoDB()

    backend_url: str

    debug: bool = False

    model_config = {"env_prefix": "wizarr_"}


SETTINGS = Settings()  # type: ignore
