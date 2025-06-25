from typing import TYPE_CHECKING, TypedDict, Literal, NotRequired, Union

if TYPE_CHECKING:
    from container import Container
    from render import Render

try:
    from .error import RenderError
    from .validations import valid_fs_path_or_raise
    from .volume_mount import VolumeMount
except ImportError:
    from error import RenderError
    from validations import valid_fs_path_or_raise
    from volume_mount import VolumeMount


class IxStorageTmpfsConfig(TypedDict):
    size: NotRequired[int]
    mode: NotRequired[str]
    uid: NotRequired[int]
    gid: NotRequired[int]


class AclConfig(TypedDict, total=False):
    path: str


class IxStorageHostPathConfig(TypedDict):
    path: NotRequired[str]  # Either this or acl.path must be set
    acl_enable: NotRequired[bool]
    acl: NotRequired[AclConfig]
    create_host_path: NotRequired[bool]
    propagation: NotRequired[Literal["shared", "slave", "private", "rshared", "rslave", "rprivate"]]
    auto_permissions: NotRequired[bool]  # Only when acl_enable is false


class IxStorageIxVolumeConfig(TypedDict):
    dataset_name: str
    acl_enable: NotRequired[bool]
    acl_entries: NotRequired[AclConfig]
    create_host_path: NotRequired[bool]
    propagation: NotRequired[Literal["shared", "slave", "private", "rshared", "rslave", "rprivate"]]
    auto_permissions: NotRequired[bool]  # Only when acl_enable is false


class IxStorageVolumeConfig(TypedDict):
    volume_name: NotRequired[str]
    nocopy: NotRequired[bool]
    auto_permissions: NotRequired[bool]


class IxStorageNfsConfig(TypedDict):
    server: str
    path: str
    options: NotRequired[list[str]]


class IxStorageCifsConfig(TypedDict):
    server: str
    path: str
    username: str
    password: str
    domain: NotRequired[str]
    options: NotRequired[list[str]]


IxStorageVolumeLikeConfigs = Union[IxStorageVolumeConfig, IxStorageNfsConfig, IxStorageCifsConfig, IxStorageTmpfsConfig]
IxStorageBindLikeConfigs = Union[IxStorageHostPathConfig, IxStorageIxVolumeConfig]
IxStorageLikeConfigs = Union[IxStorageBindLikeConfigs, IxStorageVolumeLikeConfigs]


class IxStorage(TypedDict):
    type: Literal["ix_volume", "host_path", "tmpfs", "volume", "anonymous", "temporary"]
    read_only: NotRequired[bool]

    ix_volume_config: NotRequired[IxStorageIxVolumeConfig]
    host_path_config: NotRequired[IxStorageHostPathConfig]
    tmpfs_config: NotRequired[IxStorageTmpfsConfig]
    volume_config: NotRequired[IxStorageVolumeConfig]
    nfs_config: NotRequired[IxStorageNfsConfig]
    cifs_config: NotRequired[IxStorageCifsConfig]


class Storage:
    def __init__(self, render_instance: "Render", container_instance: "Container"):
        self._container_instance = container_instance
        self._render_instance = render_instance
        self._volume_mounts: set[VolumeMount] = set()

    def add(self, mount_path: str, config: "IxStorage"):
        mount_path = valid_fs_path_or_raise(mount_path)
        if self.is_defined(mount_path):
            raise RenderError(f"Mount path [{mount_path}] already used for another volume mount")
        if self._container_instance._tmpfs.is_defined(mount_path):
            raise RenderError(f"Mount path [{mount_path}] already used for another volume mount")

        volume_mount = VolumeMount(self._render_instance, mount_path, config)
        self._volume_mounts.add(volume_mount)

    def is_defined(self, mount_path: str):
        return mount_path in [m.mount_path for m in self._volume_mounts]

    def _add_docker_socket(self, read_only: bool = True, mount_path: str = ""):
        mount_path = valid_fs_path_or_raise(mount_path)
        cfg: "IxStorage" = {
            "type": "host_path",
            "read_only": read_only,
            "host_path_config": {"path": "/var/run/docker.sock", "create_host_path": False},
        }
        self.add(mount_path, cfg)

    def _add_udev(self, read_only: bool = True, mount_path: str = ""):
        mount_path = valid_fs_path_or_raise(mount_path)
        cfg: "IxStorage" = {
            "type": "host_path",
            "read_only": read_only,
            "host_path_config": {"path": "/run/udev", "create_host_path": False},
        }
        self.add(mount_path, cfg)

    def has_mounts(self) -> bool:
        return bool(self._volume_mounts)

    def render(self):
        return [vm.render() for vm in sorted(self._volume_mounts, key=lambda vm: vm.mount_path)]
