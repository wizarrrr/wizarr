from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from container import Container
    from render import Render
    from storage import IxStorage

try:
    from .error import RenderError
    from .validations import valid_fs_path_or_raise, valid_octal_mode_or_raise
except ImportError:
    from error import RenderError
    from validations import valid_fs_path_or_raise, valid_octal_mode_or_raise


class Tmpfs:

    def __init__(self, render_instance: "Render", container_instance: "Container"):
        self._render_instance = render_instance
        self._container_instance = container_instance
        self._tmpfs: dict = {}

    def add(self, mount_path: str, config: "IxStorage"):
        mount_path = valid_fs_path_or_raise(mount_path)
        if self.is_defined(mount_path):
            raise RenderError(f"Tmpfs mount path [{mount_path}] already added")

        if self._container_instance.storage.is_defined(mount_path):
            raise RenderError(f"Tmpfs mount path [{mount_path}] already used for another volume mount")

        mount_config = config.get("tmpfs_config", {})
        size = mount_config.get("size", None)
        mode = mount_config.get("mode", None)
        uid = mount_config.get("uid", None)
        gid = mount_config.get("gid", None)

        if size is not None:
            if not isinstance(size, int):
                raise RenderError(f"Expected [size] to be an integer for [tmpfs] type, got [{size}]")
            if not size > 0:
                raise RenderError(f"Expected [size] to be greater than 0 for [tmpfs] type, got [{size}]")
            # Convert Mebibytes to Bytes
            size = size * 1024 * 1024

        if mode is not None:
            mode = valid_octal_mode_or_raise(mode)

        if uid is not None and not isinstance(uid, int):
            raise RenderError(f"Expected [uid] to be an integer for [tmpfs] type, got [{uid}]")

        if gid is not None and not isinstance(gid, int):
            raise RenderError(f"Expected [gid] to be an integer for [tmpfs] type, got [{gid}]")

        self._tmpfs[mount_path] = {}
        if size is not None:
            self._tmpfs[mount_path]["size"] = str(size)
        if mode is not None:
            self._tmpfs[mount_path]["mode"] = str(mode)
        if uid is not None:
            self._tmpfs[mount_path]["uid"] = str(uid)
        if gid is not None:
            self._tmpfs[mount_path]["gid"] = str(gid)

    def is_defined(self, mount_path: str):
        return mount_path in self._tmpfs

    def has_tmpfs(self):
        return bool(self._tmpfs)

    def render(self):
        result = []
        for mount_path, config in self._tmpfs.items():
            opts = sorted([f"{k}={v}" for k, v in config.items()])
            result.append(f"{mount_path}:{','.join(opts)}" if opts else mount_path)
        return sorted(result)
