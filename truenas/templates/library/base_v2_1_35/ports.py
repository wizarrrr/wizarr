import ipaddress
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from render import Render

try:
    from .error import RenderError
    from .validations import (
        valid_ip_or_raise,
        valid_port_mode_or_raise,
        valid_port_or_raise,
        valid_port_protocol_or_raise,
    )
except ImportError:
    from error import RenderError
    from validations import (
        valid_ip_or_raise,
        valid_port_mode_or_raise,
        valid_port_or_raise,
        valid_port_protocol_or_raise,
    )


class Ports:
    def __init__(self, render_instance: "Render"):
        self._render_instance = render_instance
        self._ports: dict[str, dict] = {}

    def _gen_port_key(self, host_port: int, host_ip: str, proto: str, ip_family: int) -> str:
        return f"{host_port}_{host_ip}_{proto}_{ip_family}"

    def _is_wildcard_ip(self, ip: str) -> bool:
        return ip in ["0.0.0.0", "::"]

    def _get_opposite_wildcard(self, ip: str) -> str:
        return "0.0.0.0" if ip == "::" else "::"

    def _get_sort_key(self, p: dict) -> str:
        return f"{p['published']}_{p['target']}_{p['protocol']}_{p.get('host_ip', '_')}"

    def _is_ports_same(self, port1: dict, port2: dict) -> bool:
        return (
            port1["published"] == port2["published"]
            and port1["target"] == port2["target"]
            and port1["protocol"] == port2["protocol"]
            and port1.get("host_ip", "_") == port2.get("host_ip", "_")
        )

    def _has_opposite_family_port(self, port_config: dict, wildcard_ports: dict) -> bool:
        comparison_port = port_config.copy()
        comparison_port["host_ip"] = self._get_opposite_wildcard(port_config["host_ip"])
        for p in wildcard_ports.values():
            if self._is_ports_same(comparison_port, p):
                return True
        return False

    def _check_port_conflicts(self, port_config: dict, ip_family: int) -> None:
        host_port = port_config["published"]
        host_ip = port_config["host_ip"]
        proto = port_config["protocol"]

        key = self._gen_port_key(host_port, host_ip, proto, ip_family)

        if key in self._ports.keys():
            raise RenderError(f"Port [{host_port}/{proto}/ipv{ip_family}] already added for [{host_ip}]")

        wildcard_ip = "0.0.0.0" if ip_family == 4 else "::"
        if host_ip != wildcard_ip:
            # Check if there is a port with same details but with wildcard IP of the same family
            wildcard_key = self._gen_port_key(host_port, wildcard_ip, proto, ip_family)
            if wildcard_key in self._ports.keys():
                raise RenderError(
                    f"Cannot bind port [{host_port}/{proto}/ipv{ip_family}] to [{host_ip}], "
                    f"already bound to [{wildcard_ip}]"
                )
        else:
            # We are adding a port with wildcard IP
            # Check if there is a port with same details but with specific IP of the same family
            for p in self._ports.values():
                # Skip if the port is not for the same family
                if ip_family != ipaddress.ip_address(p["host_ip"]).version:
                    continue

                # Make a copy of the port config
                search_port = p.copy()
                # Replace the host IP with wildcard IP
                search_port["host_ip"] = wildcard_ip
                # If the ports match, means that a port for specific IP is already added
                # and we are trying to add it again with wildcard IP. Raise an error
                if self._is_ports_same(search_port, port_config):
                    raise RenderError(
                        f"Cannot bind port [{host_port}/{proto}/ipv{ip_family}] to [{host_ip}], "
                        f"already bound to [{p['host_ip']}]"
                    )

    def _add_port(self, host_port: int, container_port: int, config: dict | None = None):
        config = config or {}
        host_port = valid_port_or_raise(host_port)
        container_port = valid_port_or_raise(container_port)
        proto = valid_port_protocol_or_raise(config.get("protocol", "tcp"))
        mode = valid_port_mode_or_raise(config.get("mode", "ingress"))

        host_ip = valid_ip_or_raise(config.get("host_ip", ""))
        ip = ipaddress.ip_address(host_ip)

        port_config = {
            "published": host_port,
            "target": container_port,
            "protocol": proto,
            "mode": mode,
            "host_ip": host_ip,
        }
        self._check_port_conflicts(port_config, ip.version)

        key = self._gen_port_key(host_port, host_ip, proto, ip.version)
        self._ports[key] = port_config
        # After all the local validations, lets validate the port with the TrueNAS API
        self._render_instance.client.validate_ip_port_combo(host_ip, host_port)

    def has_ports(self):
        return len(self._ports) > 0

    def render(self):
        specific_ports = []
        wildcard_ports = {}

        for port_config in self._ports.values():
            if self._is_wildcard_ip(port_config["host_ip"]):
                wildcard_ports[id(port_config)] = port_config.copy()
            else:
                specific_ports.append(port_config.copy())

        processed_ports = specific_ports.copy()
        for wild_port in wildcard_ports.values():
            processed_port = wild_port.copy()

            # Check if there's a matching wildcard port for the opposite IP family
            has_opposite_family = self._has_opposite_family_port(wild_port, wildcard_ports)

            if has_opposite_family:
                processed_port.pop("host_ip")

            if processed_port not in processed_ports:
                processed_ports.append(processed_port)

        return sorted(processed_ports, key=self._get_sort_key)
