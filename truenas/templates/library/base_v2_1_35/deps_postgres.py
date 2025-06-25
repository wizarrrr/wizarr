import urllib.parse
from typing import TYPE_CHECKING, TypedDict, NotRequired


if TYPE_CHECKING:
    from render import Render
    from storage import IxStorage


try:
    from .error import RenderError
    from .deps_perms import PermsContainer
    from .validations import valid_port_or_raise
except ImportError:
    from error import RenderError
    from deps_perms import PermsContainer
    from validations import valid_port_or_raise


class PostgresConfig(TypedDict):
    user: str
    password: str
    database: str
    port: NotRequired[int]
    volume: "IxStorage"


MAX_POSTGRES_VERSION = 17


class PostgresContainer:
    def __init__(
        self, render_instance: "Render", name: str, image: str, config: PostgresConfig, perms_instance: PermsContainer
    ):
        self._render_instance = render_instance
        self._name = name
        self._config = config
        self._data_dir = "/var/lib/postgresql/data"
        self._upgrade_name = f"{self._name}_upgrade"
        self._upgrade_container = None

        for key in ("user", "password", "database", "volume"):
            if key not in config:
                raise RenderError(f"Expected [{key}] to be set for postgres")

        port = valid_port_or_raise(self._get_port())

        c = self._render_instance.add_container(name, image)

        c.set_user(999, 999)
        c.healthcheck.set_test("postgres")
        c.remove_devices()
        c.add_storage(self._data_dir, config["volume"])

        common_variables = {
            "POSTGRES_USER": config["user"],
            "POSTGRES_PASSWORD": config["password"],
            "POSTGRES_DB": config["database"],
            "PGPORT": port,
        }

        for k, v in common_variables.items():
            c.environment.add_env(k, v)

        perms_instance.add_or_skip_action(
            f"{self._name}_postgres_data", config["volume"], {"uid": 999, "gid": 999, "mode": "check"}
        )

        repo = self._get_repo(
            image, ("postgres", "tensorchord/pgvecto-rs", "postgis/postgis", "ghcr.io/immich-app/postgres")
        )
        # eg we don't want to handle upgrades of pg_vector at the moment
        if repo == "postgres":
            target_major_version = self._get_target_version(image)
            upg = self._render_instance.add_container(self._upgrade_name, "postgres_upgrade_image")
            upg.set_entrypoint(["/bin/bash", "-c", "/upgrade.sh"])
            upg.restart.set_policy("on-failure", 1)
            upg.set_user(999, 999)
            upg.healthcheck.disable()
            upg.remove_devices()
            upg.add_storage(self._data_dir, config["volume"])
            for k, v in common_variables.items():
                upg.environment.add_env(k, v)

            upg.environment.add_env("TARGET_VERSION", target_major_version)
            upg.environment.add_env("DATA_DIR", self._data_dir)

            self._upgrade_container = upg

            c.depends.add_dependency(self._upgrade_name, "service_completed_successfully")

        # Store container for further configuration
        # For example: c.depends.add_dependency("other_container", "service_started")
        self._container = c

    @property
    def container(self):
        return self._container

    def add_dependency(self, container_name: str, condition: str):
        self._container.depends.add_dependency(container_name, condition)
        if self._upgrade_container:
            self._upgrade_container.depends.add_dependency(container_name, condition)

    def _get_port(self):
        return self._config.get("port") or 5432

    def _get_repo(self, image, supported_repos):
        images = self._render_instance.values["images"]
        if image not in images:
            raise RenderError(f"Image [{image}] not found in values. Available images: [{', '.join(images.keys())}]")
        repo = images[image].get("repository")
        if not repo:
            raise RenderError("Could not determine repo")
        if repo not in supported_repos:
            raise RenderError(f"Unsupported repo [{repo}] for postgres. Supported repos: {', '.join(supported_repos)}")
        return repo

    def _get_target_version(self, image):
        images = self._render_instance.values["images"]
        if image not in images:
            raise RenderError(f"Image [{image}] not found in values. Available images: [{', '.join(images.keys())}]")
        tag = images[image].get("tag", "")
        tag = str(tag)  # Account for tags like 16.6
        target_major_version = tag.split(".")[0]

        try:
            target_major_version = int(target_major_version)
        except ValueError:
            raise RenderError(f"Could not determine target major version from tag [{tag}]")

        if target_major_version > MAX_POSTGRES_VERSION:
            raise RenderError(f"Postgres version [{target_major_version}] is not supported")

        return target_major_version

    def get_url(self, variant: str):
        user = urllib.parse.quote_plus(self._config["user"])
        password = urllib.parse.quote_plus(self._config["password"])
        creds = f"{user}:{password}"
        addr = f"{self._name}:{self._get_port()}"
        db = self._config["database"]

        urls = {
            "postgres": f"postgres://{creds}@{addr}/{db}?sslmode=disable",
            "postgresql": f"postgresql://{creds}@{addr}/{db}?sslmode=disable",
            "postgresql_no_creds": f"postgresql://{addr}/{db}?sslmode=disable",
            "host_port": addr,
        }

        if variant not in urls:
            raise RenderError(f"Expected [variant] to be one of [{', '.join(urls.keys())}], got [{variant}]")
        return urls[variant]
