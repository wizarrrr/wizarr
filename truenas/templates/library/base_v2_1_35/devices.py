from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from render import Render

try:
    from .error import RenderError
    from .device import Device
except ImportError:
    from error import RenderError
    from device import Device


class Devices:
    def __init__(self, render_instance: "Render"):
        self._render_instance = render_instance
        self._devices: set[Device] = set()

        # Tracks all container device paths to make sure they are not duplicated
        self._container_device_paths: set[str] = set()
        # Scan values for devices we should automatically add
        # for example /dev/dri for gpus
        self._auto_add_devices_from_values()

    def _auto_add_devices_from_values(self):
        resources = self._render_instance.values.get("resources", {})

        if resources.get("gpus", {}).get("use_all_gpus", False):
            self.add_device("/dev/dri", "/dev/dri", allow_disallowed=True)
            if resources["gpus"].get("kfd_device_exists", False):
                self.add_device("/dev/kfd", "/dev/kfd", allow_disallowed=True)  # AMD ROCm

    def add_device(self, host_device: str, container_device: str, cgroup_perm: str = "", allow_disallowed=False):
        # Host device can be mapped to multiple container devices,
        # so we only make sure container devices are not duplicated
        if container_device in self._container_device_paths:
            raise RenderError(f"Device with container path [{container_device}] already added")

        self._devices.add(Device(host_device, container_device, cgroup_perm, allow_disallowed))
        self._container_device_paths.add(container_device)

    def add_usb_bus(self):
        self.add_device("/dev/bus/usb", "/dev/bus/usb", allow_disallowed=True)

    def _add_snd_device(self):
        self.add_device("/dev/snd", "/dev/snd", allow_disallowed=True)

    def _add_tun_device(self):
        self.add_device("/dev/net/tun", "/dev/net/tun", allow_disallowed=True)

    def has_devices(self):
        return len(self._devices) > 0

    # Mainly will be used from dependencies
    # There is no reason to pass devices to
    # redis or postgres for example
    def remove_devices(self):
        self._devices.clear()
        self._container_device_paths.clear()

    # Check if there are any gpu devices
    # Used to determine if we should add groups
    # like 'video' to the container
    def has_gpus(self):
        for d in self._devices:
            if d.host_device == "/dev/dri":
                return True
        return False

    def render(self) -> list[str]:
        return sorted([d.render() for d in self._devices])
