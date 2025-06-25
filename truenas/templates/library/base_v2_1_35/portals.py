from typing import TYPE_CHECKING

import copy

if TYPE_CHECKING:
    from render import Render

try:
    from .error import RenderError
    from .validations import valid_portal_scheme_or_raise, valid_http_path_or_raise, valid_port_or_raise
except ImportError:
    from error import RenderError
    from validations import valid_portal_scheme_or_raise, valid_http_path_or_raise, valid_port_or_raise


class Portals:
    def __init__(self, render_instance: "Render"):
        self._render_instance = render_instance
        self._portals: set[Portal] = set()

    def add(self, port: dict, config: dict | None = None):
        config = copy.deepcopy((config or {}))
        port = copy.deepcopy((port or {}))
        # If its not published, portal does not make sense
        if port.get("bind_mode", "") != "published":
            return

        name = config.get("name", "Web UI")

        if name in [p._name for p in self._portals]:
            raise RenderError(f"Portal [{name}] already added")

        host = config.get("host", None)
        host_ips = port.get("host_ips", [])
        if not isinstance(host_ips, list):
            raise RenderError("Expected [host_ips] to be a list of strings")

        # Remove wildcard IPs
        if "::" in host_ips:
            host_ips.remove("::")
        if "0.0.0.0" in host_ips:
            host_ips.remove("0.0.0.0")

        # If host is not set, use the first host_ip (if it exists)
        if not host and len(host_ips) >= 1:
            host = host_ips[0]

        config["host"] = host
        if not config.get("port"):
            config["port"] = port.get("port_number", 0)

        self._portals.add(Portal(name, config))

    def render(self):
        return [p.render() for _, p in sorted([(p._name, p) for p in self._portals])]


class Portal:
    def __init__(self, name: str, config: dict):
        self._name = name
        self._scheme = valid_portal_scheme_or_raise(config.get("scheme", "http"))
        self._host = config.get("host", "0.0.0.0") or "0.0.0.0"
        self._port = valid_port_or_raise(config.get("port", 0))
        self._path = valid_http_path_or_raise(config.get("path", "/"))

    def render(self):
        return {
            "name": self._name,
            "scheme": self._scheme,
            "host": self._host,
            "port": self._port,
            "path": self._path,
        }
