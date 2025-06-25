from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from render import Render
    from container import Container

try:
    from .error import RenderError
    from .validations import valid_sysctl_or_raise
except ImportError:
    from error import RenderError
    from validations import valid_sysctl_or_raise


class Sysctls:
    def __init__(self, render_instance: "Render", container_instance: "Container"):
        self._render_instance = render_instance
        self._container_instance = container_instance
        self._sysctls: dict = {}

    def add(self, key: str, value):
        key = key.strip()
        if not key:
            raise RenderError("Sysctls key cannot be empty")
        if value is None:
            raise RenderError(f"Sysctl [{key}] requires a value")
        if key in self._sysctls:
            raise RenderError(f"Sysctl [{key}] already added")
        self._sysctls[key] = str(value)

    def has_sysctls(self):
        return bool(self._sysctls)

    def render(self):
        if not self.has_sysctls():
            return {}
        host_net = self._container_instance._network_mode == "host"
        return {valid_sysctl_or_raise(k, host_net): v for k, v in self._sysctls.items()}
