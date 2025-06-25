from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from render import Render
    from storage import IxStorage

try:
    from .configs import ContainerConfigs
    from .depends import Depends
    from .deploy import Deploy
    from .device_cgroup_rules import DeviceCGroupRules
    from .devices import Devices
    from .dns import Dns
    from .environment import Environment
    from .error import RenderError
    from .expose import Expose
    from .extra_hosts import ExtraHosts
    from .formatter import escape_dollar, get_image_with_hashed_data
    from .healthcheck import Healthcheck
    from .labels import Labels
    from .ports import Ports
    from .restart import RestartPolicy
    from .tmpfs import Tmpfs
    from .validations import (
        valid_cap_or_raise,
        valid_cgroup_or_raise,
        valid_ipc_mode_or_raise,
        valid_network_mode_or_raise,
        valid_port_bind_mode_or_raise,
        valid_port_mode_or_raise,
        valid_pull_policy_or_raise,
    )
    from .security_opts import SecurityOpts
    from .storage import Storage
    from .sysctls import Sysctls
except ImportError:
    from configs import ContainerConfigs
    from depends import Depends
    from deploy import Deploy
    from device_cgroup_rules import DeviceCGroupRules
    from devices import Devices
    from dns import Dns
    from environment import Environment
    from error import RenderError
    from expose import Expose
    from extra_hosts import ExtraHosts
    from formatter import escape_dollar, get_image_with_hashed_data
    from healthcheck import Healthcheck
    from labels import Labels
    from ports import Ports
    from restart import RestartPolicy
    from tmpfs import Tmpfs
    from validations import (
        valid_cap_or_raise,
        valid_cgroup_or_raise,
        valid_ipc_mode_or_raise,
        valid_network_mode_or_raise,
        valid_port_bind_mode_or_raise,
        valid_port_mode_or_raise,
        valid_pull_policy_or_raise,
    )
    from security_opts import SecurityOpts
    from storage import Storage
    from sysctls import Sysctls


class Container:
    def __init__(self, render_instance: "Render", name: str, image: str):
        self._render_instance = render_instance

        self._name: str = name
        self._image: str = self._resolve_image(image)
        self._build_image: str = ""
        self._pull_policy: str = ""
        self._user: str = ""
        self._tty: bool = False
        self._stdin_open: bool = False
        self._init: bool | None = None
        self._read_only: bool | None = None
        self._extra_hosts: ExtraHosts = ExtraHosts(self._render_instance)
        self._hostname: str = ""
        self._cap_drop: set[str] = set(["ALL"])  # Drop all capabilities by default and add caps granularly
        self._cap_add: set[str] = set()
        self._security_opt: SecurityOpts = SecurityOpts(self._render_instance)
        self._privileged: bool = False
        self._group_add: set[int | str] = set()
        self._network_mode: str = ""
        self._entrypoint: list[str] = []
        self._command: list[str] = []
        self._grace_period: int | None = None
        self._shm_size: int | None = None
        self._storage: Storage = Storage(self._render_instance, self)
        self._tmpfs: Tmpfs = Tmpfs(self._render_instance, self)
        self._ipc_mode: str | None = None
        self._cgroup: str | None = None
        self._device_cgroup_rules: DeviceCGroupRules = DeviceCGroupRules(self._render_instance)
        self.sysctls: Sysctls = Sysctls(self._render_instance, self)
        self.configs: ContainerConfigs = ContainerConfigs(self._render_instance, self._render_instance.configs)
        self.deploy: Deploy = Deploy(self._render_instance)
        self.networks: set[str] = set()
        self.devices: Devices = Devices(self._render_instance)
        self.environment: Environment = Environment(self._render_instance, self.deploy.resources)
        self.dns: Dns = Dns(self._render_instance)
        self.depends: Depends = Depends(self._render_instance)
        self.healthcheck: Healthcheck = Healthcheck(self._render_instance)
        self.labels: Labels = Labels(self._render_instance)
        self.restart: RestartPolicy = RestartPolicy(self._render_instance)
        self.ports: Ports = Ports(self._render_instance)
        self.expose: Expose = Expose(self._render_instance)

        self._auto_set_network_mode()
        self._auto_add_labels()
        self._auto_add_groups()

    def _auto_add_groups(self):
        self.add_group(568)

    def _auto_set_network_mode(self):
        if self._render_instance.values.get("network", {}).get("host_network", False):
            self.set_network_mode("host")

    def _auto_add_labels(self):
        labels = self._render_instance.values.get("labels", [])
        if not labels:
            return

        for label in labels:
            containers = label.get("containers", [])
            if not containers:
                raise RenderError(f'Label [{label.get("key", "")}] must have at least one container')

            if self._name in containers:
                self.labels.add_label(label["key"], label["value"])

    def _resolve_image(self, image: str):
        images = self._render_instance.values["images"]
        if image not in images:
            raise RenderError(
                f"Image [{image}] not found in values. " f"Available images: [{', '.join(images.keys())}]"
            )
        repo = images[image].get("repository", "")
        tag = images[image].get("tag", "")

        if not repo:
            raise RenderError(f"Repository not found for image [{image}]")
        if not tag:
            raise RenderError(f"Tag not found for image [{image}]")

        return f"{repo}:{tag}"

    def build_image(self, content: list[str | None]):
        dockerfile = f"FROM {self._image}\n"
        for line in content:
            line = line.strip() if line else ""
            if not line:
                continue
            if line.startswith("FROM"):
                # TODO: This will also block multi-stage builds
                # We can revisit this later if we need it
                raise RenderError(
                    "FROM cannot be used in build image. Define the base image when creating the container."
                )
            dockerfile += line + "\n"

        self._build_image = dockerfile
        self._image = get_image_with_hashed_data(self._image, dockerfile)

    def set_pull_policy(self, pull_policy: str):
        self._pull_policy = valid_pull_policy_or_raise(pull_policy)

    def set_user(self, user: int, group: int):
        for i in (user, group):
            if not isinstance(i, int) or i < 0:
                raise RenderError(f"User/Group [{i}] is not valid")
        self._user = f"{user}:{group}"

    def add_extra_host(self, host: str, ip: str):
        self._extra_hosts.add_host(host, ip)

    def add_group(self, group: int | str):
        if isinstance(group, str):
            group = str(group).strip()
            if group.isdigit():
                raise RenderError(f"Group is a number [{group}] but passed as a string")

        if group in self._group_add:
            raise RenderError(f"Group [{group}] already added")
        self._group_add.add(group)

    def get_additional_groups(self) -> list[int | str]:
        result = []
        if self.deploy.resources.has_gpus() or self.devices.has_gpus():
            result.append(44)  # video
            result.append(107)  # render
        return result

    def get_current_groups(self) -> list[str]:
        result = [str(g) for g in self._group_add]
        result.extend([str(g) for g in self.get_additional_groups()])
        return result

    def set_tty(self, enabled: bool = False):
        self._tty = enabled

    def set_stdin(self, enabled: bool = False):
        self._stdin_open = enabled

    def set_ipc_mode(self, ipc_mode: str):
        self._ipc_mode = valid_ipc_mode_or_raise(ipc_mode, self._render_instance.container_names())

    def add_device_cgroup_rule(self, dev_grp_rule: str):
        self._device_cgroup_rules.add_rule(dev_grp_rule)

    def set_cgroup(self, cgroup: str):
        self._cgroup = valid_cgroup_or_raise(cgroup)

    def set_init(self, enabled: bool = False):
        self._init = enabled

    def set_read_only(self, enabled: bool = False):
        self._read_only = enabled

    def set_hostname(self, hostname: str):
        self._hostname = hostname

    def set_grace_period(self, grace_period: int):
        if grace_period < 0:
            raise RenderError(f"Grace period [{grace_period}] cannot be negative")
        self._grace_period = grace_period

    def set_privileged(self, enabled: bool = False):
        self._privileged = enabled

    def clear_caps(self):
        self._cap_add.clear()
        self._cap_drop.clear()

    def add_caps(self, caps: list[str]):
        for c in caps:
            if c in self._cap_add:
                raise RenderError(f"Capability [{c}] already added")
            self._cap_add.add(valid_cap_or_raise(c))

    def add_security_opt(self, key: str, value: str | bool | None = None, arg: str | None = None):
        self._security_opt.add_opt(key, value, arg)

    def remove_security_opt(self, key: str):
        self._security_opt.remove_opt(key)

    def set_network_mode(self, mode: str):
        self._network_mode = valid_network_mode_or_raise(mode, self._render_instance.container_names())

    def add_port(self, port_config: dict | None = None, dev_config: dict | None = None):
        port_config = port_config or {}
        dev_config = dev_config or {}
        # Merge port_config and dev_config (dev_config has precedence)
        config = port_config | dev_config
        bind_mode = valid_port_bind_mode_or_raise(config.get("bind_mode", ""))
        # Skip port if its neither published nor exposed
        if not bind_mode:
            return

        # Collect port config
        mode = valid_port_mode_or_raise(config.get("mode", "ingress"))
        host_port = config.get("port_number", 0)
        container_port = config.get("container_port", 0) or host_port
        protocol = config.get("protocol", "tcp")
        host_ips = config.get("host_ips") or ["0.0.0.0", "::"]
        if not isinstance(host_ips, list):
            raise RenderError(f"Expected [host_ips] to be a list, got [{host_ips}]")

        if bind_mode == "published":
            for host_ip in host_ips:
                self.ports._add_port(
                    host_port, container_port, {"protocol": protocol, "host_ip": host_ip, "mode": mode}
                )
        elif bind_mode == "exposed":
            self.expose.add_port(container_port, protocol)

    def set_entrypoint(self, entrypoint: list[str]):
        self._entrypoint = [escape_dollar(str(e)) for e in entrypoint]

    def set_command(self, command: list[str]):
        self._command = [escape_dollar(str(e)) for e in command]

    def add_storage(self, mount_path: str, config: "IxStorage"):
        if config.get("type", "") == "tmpfs":
            self._tmpfs.add(mount_path, config)
        else:
            self._storage.add(mount_path, config)

    def add_docker_socket(self, read_only: bool = True, mount_path: str = "/var/run/docker.sock"):
        self.add_group(999)
        self._storage._add_docker_socket(read_only, mount_path)

    def add_udev(self, read_only: bool = True, mount_path: str = "/run/udev"):
        self._storage._add_udev(read_only, mount_path)

    def add_tun_device(self):
        self.devices._add_tun_device()

    def add_snd_device(self):
        self.add_group(29)
        self.devices._add_snd_device()

    def set_shm_size_mb(self, size: int):
        self._shm_size = size

    # Easily remove devices from the container
    # Useful in dependencies like postgres and redis
    # where there is no need to pass devices to them
    def remove_devices(self):
        self.deploy.resources.remove_devices()
        self.devices.remove_devices()

    @property
    def storage(self):
        return self._storage

    def render(self) -> dict[str, Any]:
        if self._network_mode and self.networks:
            raise RenderError("Cannot set both [network_mode] and [networks]")

        result = {
            "image": self._image,
            "platform": "linux/amd64",
            "tty": self._tty,
            "stdin_open": self._stdin_open,
            "restart": self.restart.render(),
        }

        if self._pull_policy:
            result["pull_policy"] = self._pull_policy

        if self.healthcheck.has_healthcheck():
            result["healthcheck"] = self.healthcheck.render()

        if self._hostname:
            result["hostname"] = self._hostname

        if self._build_image:
            result["build"] = {"tags": [self._image], "dockerfile_inline": self._build_image}

        if self.configs.has_configs():
            result["configs"] = self.configs.render()

        if self._ipc_mode is not None:
            result["ipc"] = self._ipc_mode

        if self._device_cgroup_rules.has_rules():
            result["device_cgroup_rules"] = self._device_cgroup_rules.render()

        if self._cgroup is not None:
            result["cgroup"] = self._cgroup

        if self._extra_hosts.has_hosts():
            result["extra_hosts"] = self._extra_hosts.render()

        if self._init is not None:
            result["init"] = self._init

        if self._read_only is not None:
            result["read_only"] = self._read_only

        if self._grace_period is not None:
            result["stop_grace_period"] = f"{self._grace_period}s"

        if self._user:
            result["user"] = self._user

        for g in self.get_additional_groups():
            self.add_group(g)

        if self._group_add:
            result["group_add"] = sorted(self._group_add, key=lambda g: (isinstance(g, str), g))

        if self._shm_size is not None:
            result["shm_size"] = f"{self._shm_size}M"

        if self._privileged is not None:
            result["privileged"] = self._privileged

        if self._cap_drop:
            result["cap_drop"] = sorted(self._cap_drop)

        if self._cap_add:
            result["cap_add"] = sorted(self._cap_add)

        if self._security_opt.has_opts():
            result["security_opt"] = self._security_opt.render()

        if self._network_mode:
            result["network_mode"] = self._network_mode

        if self.sysctls.has_sysctls():
            result["sysctls"] = self.sysctls.render()

        if self._network_mode != "host":
            if self.ports.has_ports():
                result["ports"] = self.ports.render()

            if self.expose.has_ports():
                result["expose"] = self.expose.render()

        if self._entrypoint:
            result["entrypoint"] = self._entrypoint

        if self._command:
            result["command"] = self._command

        if self.devices.has_devices():
            result["devices"] = self.devices.render()

        if self.deploy.has_deploy():
            result["deploy"] = self.deploy.render()

        if self.environment.has_variables():
            result["environment"] = self.environment.render()

        if self.labels.has_labels():
            result["labels"] = self.labels.render()

        if self.dns.has_dns_nameservers():
            result["dns"] = self.dns.render_dns_nameservers()

        if self.dns.has_dns_searches():
            result["dns_search"] = self.dns.render_dns_searches()

        if self.dns.has_dns_opts():
            result["dns_opt"] = self.dns.render_dns_opts()

        if self.depends.has_dependencies():
            result["depends_on"] = self.depends.render()

        if self._storage.has_mounts():
            result["volumes"] = self._storage.render()

        if self._tmpfs.has_tmpfs():
            result["tmpfs"] = self._tmpfs.render()

        return result
