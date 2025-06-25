import re
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from render import Render

try:
    from .error import RenderError
except ImportError:
    from error import RenderError

DEFAULT_CPUS = 2.0
DEFAULT_MEMORY = 4096


class Resources:
    def __init__(self, render_instance: "Render"):
        self._render_instance = render_instance
        self._limits: dict = {}
        self._reservations: dict = {}
        self._nvidia_ids: set[str] = set()
        self._auto_add_cpu_from_values()
        self._auto_add_memory_from_values()
        self._auto_add_gpus_from_values()

    def _set_cpu(self, cpus: Any):
        c = str(cpus)
        if not re.match(r"^[1-9][0-9]*(\.[0-9]+)?$", c):
            raise RenderError(f"Expected cpus to be a number or a float (minimum 1.0), got [{cpus}]")
        self._limits.update({"cpus": c})

    def _set_memory(self, memory: Any):
        m = str(memory)
        if not re.match(r"^[1-9][0-9]*$", m):
            raise RenderError(f"Expected memory to be a number, got [{memory}]")
        self._limits.update({"memory": f"{m}M"})

    def _auto_add_cpu_from_values(self):
        resources = self._render_instance.values.get("resources", {})
        self._set_cpu(resources.get("limits", {}).get("cpus", DEFAULT_CPUS))

    def _auto_add_memory_from_values(self):
        resources = self._render_instance.values.get("resources", {})
        self._set_memory(resources.get("limits", {}).get("memory", DEFAULT_MEMORY))

    def _auto_add_gpus_from_values(self):
        resources = self._render_instance.values.get("resources", {})
        gpus = resources.get("gpus", {}).get("nvidia_gpu_selection", {})
        if not gpus:
            return

        for pci, gpu in gpus.items():
            if gpu.get("use_gpu", False):
                if not gpu.get("uuid"):
                    raise RenderError(f"Expected [uuid] to be set for GPU in slot [{pci}] in [nvidia_gpu_selection]")
                self._nvidia_ids.add(gpu["uuid"])

        if self._nvidia_ids:
            if not self._reservations:
                self._reservations["devices"] = []
            self._reservations["devices"].append(
                {
                    "capabilities": ["gpu"],
                    "driver": "nvidia",
                    "device_ids": sorted(self._nvidia_ids),
                }
            )

    # This is only used on ix-app that we allow
    # disabling cpus and memory. GPUs are only added
    # if the user has requested them.
    def remove_cpus_and_memory(self):
        self._limits.pop("cpus", None)
        self._limits.pop("memory", None)

    # Mainly will be used from dependencies
    # There is no reason to pass devices to
    # redis or postgres for example
    def remove_devices(self):
        self._reservations.pop("devices", None)

    def set_profile(self, profile: str):
        cpu, memory = profile_mapping(profile)
        self._set_cpu(cpu)
        self._set_memory(memory)

    def has_resources(self):
        return len(self._limits) > 0 or len(self._reservations) > 0

    def has_gpus(self):
        gpu_devices = [d for d in self._reservations.get("devices", []) if "gpu" in d["capabilities"]]
        return len(gpu_devices) > 0

    def render(self):
        result = {}
        if self._limits:
            result["limits"] = self._limits
        if self._reservations:
            result["reservations"] = self._reservations

        return result


def profile_mapping(profile: str):
    profiles = {
        "low": (1, 512),
        "medium": (2, 1024),
    }

    if profile not in profiles:
        raise RenderError(
            f"Resource profile [{profile}] is not valid. Valid options are: [{', '.join(profiles.keys())}]"
        )

    return profiles[profile]
