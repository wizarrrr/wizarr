from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from render import Render
    from storage import IxStorage

try:
    from .error import RenderError
    from .formatter import merge_dicts_no_overwrite
    from .volume_mount_types import BindMountType, VolumeMountType
    from .volume_sources import HostPathSource, IxVolumeSource, CifsSource, NfsSource, VolumeSource
except ImportError:
    from error import RenderError
    from formatter import merge_dicts_no_overwrite
    from volume_mount_types import BindMountType, VolumeMountType
    from volume_sources import HostPathSource, IxVolumeSource, CifsSource, NfsSource, VolumeSource


class VolumeMount:
    def __init__(self, render_instance: "Render", mount_path: str, config: "IxStorage"):
        self._render_instance = render_instance
        self.mount_path: str = mount_path

        storage_type: str = config.get("type", "")
        if not storage_type:
            raise RenderError("Expected [type] to be set for volume mounts.")

        match storage_type:
            case "host_path":
                spec_type = "bind"
                mount_config = config.get("host_path_config")
                if mount_config is None:
                    raise RenderError("Expected [host_path_config] to be set for [host_path] type.")
                mount_type_specific_definition = BindMountType(self._render_instance, mount_config).render()
                source = HostPathSource(self._render_instance, mount_config).get()
            case "ix_volume":
                spec_type = "bind"
                mount_config = config.get("ix_volume_config")
                if mount_config is None:
                    raise RenderError("Expected [ix_volume_config] to be set for [ix_volume] type.")
                mount_type_specific_definition = BindMountType(self._render_instance, mount_config).render()
                source = IxVolumeSource(self._render_instance, mount_config).get()
            case "nfs":
                spec_type = "volume"
                mount_config = config.get("nfs_config")
                if mount_config is None:
                    raise RenderError("Expected [nfs_config] to be set for [nfs] type.")
                mount_type_specific_definition = VolumeMountType(self._render_instance, mount_config).render()
                source = NfsSource(self._render_instance, mount_config).get()
            case "cifs":
                spec_type = "volume"
                mount_config = config.get("cifs_config")
                if mount_config is None:
                    raise RenderError("Expected [cifs_config] to be set for [cifs] type.")
                mount_type_specific_definition = VolumeMountType(self._render_instance, mount_config).render()
                source = CifsSource(self._render_instance, mount_config).get()
            case "volume":
                spec_type = "volume"
                mount_config = config.get("volume_config")
                if mount_config is None:
                    raise RenderError("Expected [volume_config] to be set for [volume] type.")
                mount_type_specific_definition = VolumeMountType(self._render_instance, mount_config).render()
                source = VolumeSource(self._render_instance, mount_config).get()
            case "temporary":
                spec_type = "volume"
                mount_config = config.get("volume_config")
                if mount_config is None:
                    raise RenderError("Expected [volume_config] to be set for [temporary] type.")
                mount_type_specific_definition = VolumeMountType(self._render_instance, mount_config).render()
                source = VolumeSource(self._render_instance, mount_config).get()
            case "anonymous":
                spec_type = "volume"
                mount_config = config.get("volume_config") or {}
                mount_type_specific_definition = VolumeMountType(self._render_instance, mount_config).render()
                source = None
            case _:
                raise RenderError(f"Storage type [{storage_type}] is not supported for volume mounts.")

        common_spec = {"type": spec_type, "target": self.mount_path, "read_only": config.get("read_only", False)}
        if source is not None:
            common_spec["source"] = source
            self._render_instance.volumes.add_volume(source, storage_type, mount_config)  # type: ignore

        self.volume_mount_spec = merge_dicts_no_overwrite(common_spec, mount_type_specific_definition)

    def render(self) -> dict:
        return self.volume_mount_spec
