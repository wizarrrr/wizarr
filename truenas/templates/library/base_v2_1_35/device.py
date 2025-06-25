try:
    from .error import RenderError
    from .validations import valid_fs_path_or_raise, allowed_device_or_raise, valid_cgroup_perm_or_raise
except ImportError:
    from error import RenderError
    from validations import valid_fs_path_or_raise, allowed_device_or_raise, valid_cgroup_perm_or_raise


class Device:
    def __init__(self, host_device: str, container_device: str, cgroup_perm: str = "", allow_disallowed=False):
        hd = valid_fs_path_or_raise(host_device.rstrip("/"))
        cd = valid_fs_path_or_raise(container_device.rstrip("/"))
        if not hd or not cd:
            raise RenderError(
                "Expected [host_device] and [container_device] to be set. "
                f"Got host_device [{host_device}] and container_device [{container_device}]"
            )

        cgroup_perm = valid_cgroup_perm_or_raise(cgroup_perm)
        if not allow_disallowed:
            hd = allowed_device_or_raise(hd)

        self.cgroup_perm: str = cgroup_perm
        self.host_device: str = hd
        self.container_device: str = cd

    def render(self):
        result = f"{self.host_device}:{self.container_device}"
        if self.cgroup_perm:
            result += f":{self.cgroup_perm}"
        return result
