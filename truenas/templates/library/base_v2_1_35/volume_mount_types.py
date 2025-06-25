from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from render import Render
    from storage import IxStorageVolumeConfig, IxStorageBindLikeConfigs


try:
    from .validations import valid_host_path_propagation
except ImportError:
    from validations import valid_host_path_propagation


class BindMountType:
    def __init__(self, render_instance: "Render", config: "IxStorageBindLikeConfigs"):
        self._render_instance = render_instance
        self.spec: dict = {}

        propagation = valid_host_path_propagation(config.get("propagation", "rprivate"))
        create_host_path = config.get("create_host_path", False)

        self.spec: dict = {
            "bind": {
                "create_host_path": create_host_path,
                "propagation": propagation,
            }
        }

    def render(self) -> dict:
        """Render the bind mount specification."""
        return self.spec


class VolumeMountType:
    def __init__(self, render_instance: "Render", config: "IxStorageVolumeConfig"):
        self._render_instance = render_instance
        self.spec: dict = {}

        self.spec: dict = {"volume": {"nocopy": config.get("nocopy", False)}}

    def render(self) -> dict:
        """Render the volume mount specification."""
        return self.spec
