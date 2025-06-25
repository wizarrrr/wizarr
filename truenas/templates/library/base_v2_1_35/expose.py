from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from render import Render

try:
    from .error import RenderError
    from .validations import valid_port_or_raise, valid_port_protocol_or_raise
except ImportError:
    from error import RenderError
    from validations import valid_port_or_raise, valid_port_protocol_or_raise


class Expose:
    def __init__(self, render_instance: "Render"):
        self._render_instance = render_instance
        self._ports: set[str] = set()

    def add_port(self, port: int, protocol: str = "tcp"):
        port = valid_port_or_raise(port)
        protocol = valid_port_protocol_or_raise(protocol)
        key = f"{port}/{protocol}"
        if key in self._ports:
            raise RenderError(f"Exposed port [{port}/{protocol}] already added")
        self._ports.add(key)

    def has_ports(self):
        return len(self._ports) > 0

    def render(self):
        return sorted(self._ports)
