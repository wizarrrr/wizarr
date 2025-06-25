import ipaddress
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from render import Render

try:
    from .error import RenderError
except ImportError:
    from error import RenderError


class ExtraHosts:
    def __init__(self, render_instance: "Render"):
        self._render_instance = render_instance
        self._extra_hosts: dict[str, str] = {}

    def add_host(self, host: str, ip: str):
        if not ip == "host-gateway":
            try:
                ipaddress.ip_address(ip)
            except ValueError:
                raise RenderError(f"Invalid IP address [{ip}] for host [{host}]")

        if host in self._extra_hosts:
            raise RenderError(f"Host [{host}] already added with [{self._extra_hosts[host]}]")
        self._extra_hosts[host] = ip

    def has_hosts(self):
        return len(self._extra_hosts) > 0

    def render(self):
        return {host: ip for host, ip in self._extra_hosts.items()}
