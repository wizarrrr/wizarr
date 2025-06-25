from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from render import Render

try:
    from .deps_postgres import PostgresContainer, PostgresConfig
    from .deps_redis import RedisContainer, RedisConfig
    from .deps_mariadb import MariadbContainer, MariadbConfig
    from .deps_mongodb import MongoDBContainer, MongoDBConfig
    from .deps_perms import PermsContainer
except ImportError:
    from deps_postgres import PostgresContainer, PostgresConfig
    from deps_redis import RedisContainer, RedisConfig
    from deps_mariadb import MariadbContainer, MariadbConfig
    from deps_mongodb import MongoDBContainer, MongoDBConfig
    from deps_perms import PermsContainer


class Deps:
    def __init__(self, render_instance: "Render"):
        self._render_instance = render_instance

    def perms(self, name: str):
        return PermsContainer(self._render_instance, name)

    def postgres(self, name: str, image: str, config: PostgresConfig, perms_instance: PermsContainer):
        return PostgresContainer(self._render_instance, name, image, config, perms_instance)

    def redis(self, name: str, image: str, config: RedisConfig, perms_instance: PermsContainer):
        return RedisContainer(self._render_instance, name, image, config, perms_instance)

    def mariadb(self, name: str, image: str, config: MariadbConfig, perms_instance: PermsContainer):
        return MariadbContainer(self._render_instance, name, image, config, perms_instance)

    def mongodb(self, name: str, image: str, config: MongoDBConfig, perms_instance: PermsContainer):
        return MongoDBContainer(self._render_instance, name, image, config, perms_instance)
