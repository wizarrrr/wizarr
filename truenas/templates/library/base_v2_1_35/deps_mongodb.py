import urllib.parse
from typing import TYPE_CHECKING, TypedDict


if TYPE_CHECKING:
    from render import Render
    from storage import IxStorage


try:
    from .error import RenderError
    from .deps_perms import PermsContainer
except ImportError:
    from error import RenderError
    from deps_perms import PermsContainer


class MongoDBConfig(TypedDict):
    user: str
    password: str
    database: str
    volume: "IxStorage"


class MongoDBContainer:
    def __init__(
        self, render_instance: "Render", name: str, image: str, config: MongoDBConfig, perms_instance: PermsContainer
    ):
        self._render_instance = render_instance
        self._name = name
        self._config = config
        self._data_dir = "/data/db"

        for key in ("user", "password", "database", "volume"):
            if key not in config:
                raise RenderError(f"Expected [{key}] to be set for mongodb")

        c = self._render_instance.add_container(name, image)

        c.set_user(999, 999)
        c.healthcheck.set_test("mongodb")
        c.remove_devices()
        c.add_storage(self._data_dir, config["volume"])

        c.environment.add_env("MONGO_INITDB_ROOT_USERNAME", config["user"])
        c.environment.add_env("MONGO_INITDB_ROOT_PASSWORD", config["password"])
        c.environment.add_env("MONGO_INITDB_DATABASE", config["database"])

        perms_instance.add_or_skip_action(
            f"{self._name}_mongodb_data", config["volume"], {"uid": 999, "gid": 999, "mode": "check"}
        )

        self._get_repo(image, ("mongodb"))

        # Store container for further configuration
        # For example: c.depends.add_dependency("other_container", "service_started")
        self._container = c

    @property
    def container(self):
        return self._container

    def _get_port(self):
        return self._config.get("port") or 27017

    def _get_repo(self, image, supported_repos):
        images = self._render_instance.values["images"]
        if image not in images:
            raise RenderError(f"Image [{image}] not found in values. Available images: [{', '.join(images.keys())}]")
        repo = images[image].get("repository")
        if not repo:
            raise RenderError("Could not determine repo")
        if repo not in supported_repos:
            raise RenderError(f"Unsupported repo [{repo}] for mongodb. Supported repos: {', '.join(supported_repos)}")
        return repo

    def get_url(self, variant: str):
        user = urllib.parse.quote_plus(self._config["user"])
        password = urllib.parse.quote_plus(self._config["password"])
        creds = f"{user}:{password}"
        addr = f"{self._name}:{self._get_port()}"
        db = self._config["database"]

        urls = {
            "mongodb": f"mongodb://{creds}@{addr}/{db}",
            "host_port": addr,
        }

        if variant not in urls:
            raise RenderError(f"Expected [variant] to be one of [{', '.join(urls.keys())}], got [{variant}]")
        return urls[variant]
