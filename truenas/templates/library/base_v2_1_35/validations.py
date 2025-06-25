import re
import ipaddress
from pathlib import Path


try:
    from .error import RenderError
except ImportError:
    from error import RenderError

OCTAL_MODE_REGEX = re.compile(r"^0[0-7]{3}$")
RESTRICTED_IN: tuple[Path, ...] = (Path("/mnt"), Path("/"))
RESTRICTED: tuple[Path, ...] = (
    Path("/mnt/.ix-apps"),
    Path("/data"),
    Path("/var/db"),
    Path("/root"),
    Path("/conf"),
    Path("/audit"),
    Path("/var/run/middleware"),
    Path("/home"),
    Path("/boot"),
    Path("/var/log"),
)


def valid_security_opt_or_raise(opt: str):
    if ":" in opt or "=" in opt:
        raise RenderError(f"Security Option [{opt}] cannot contain [:] or [=]. Pass value as an argument")
    valid_opts = ["apparmor", "no-new-privileges", "seccomp", "systempaths", "label"]
    if opt not in valid_opts:
        raise RenderError(f"Security Option [{opt}] is not valid. Valid options are: [{', '.join(valid_opts)}]")

    return opt


def valid_port_bind_mode_or_raise(status: str):
    valid_statuses = ("published", "exposed", "")
    if status not in valid_statuses:
        raise RenderError(f"Invalid port status [{status}]")
    return status


def valid_pull_policy_or_raise(pull_policy: str):
    valid_policies = ("missing", "always", "never", "build")
    if pull_policy not in valid_policies:
        raise RenderError(f"Pull policy [{pull_policy}] is not valid. Valid options are: [{', '.join(valid_policies)}]")
    return pull_policy


def valid_ipc_mode_or_raise(ipc_mode: str, containers: list[str]):
    valid_modes = ("", "host", "private", "shareable", "none")
    if ipc_mode in valid_modes:
        return ipc_mode
    if ipc_mode.startswith("container:"):
        if ipc_mode[10:] not in containers:
            raise RenderError(f"IPC mode [{ipc_mode}] is not valid. Container [{ipc_mode[10:]}] does not exist")
        return ipc_mode
    raise RenderError(f"IPC mode [{ipc_mode}] is not valid. Valid options are: [{', '.join(valid_modes)}]")


def valid_sysctl_or_raise(sysctl: str, host_network: bool):
    if not sysctl:
        raise RenderError("Sysctl cannot be empty")
    if host_network and sysctl.startswith("net."):
        raise RenderError(f"Sysctl [{sysctl}] cannot start with [net.] when host network is enabled")

    valid_sysctls = [
        "kernel.msgmax",
        "kernel.msgmnb",
        "kernel.msgmni",
        "kernel.sem",
        "kernel.shmall",
        "kernel.shmmax",
        "kernel.shmmni",
        "kernel.shm_rmid_forced",
    ]
    # https://docs.docker.com/reference/cli/docker/container/run/#currently-supported-sysctls
    if not sysctl.startswith("fs.mqueue.") and not sysctl.startswith("net.") and sysctl not in valid_sysctls:
        raise RenderError(
            f"Sysctl [{sysctl}] is not valid. Valid options are: [{', '.join(valid_sysctls)}], [net.*], [fs.mqueue.*]"
        )
    return sysctl


def valid_redis_password_or_raise(password: str):
    forbidden_chars = [" ", "'", "#"]
    for char in forbidden_chars:
        if char in password:
            raise RenderError(f"Redis password cannot contain [{char}]")


def valid_octal_mode_or_raise(mode: str):
    mode = str(mode)
    if not OCTAL_MODE_REGEX.match(mode):
        raise RenderError(f"Expected [mode] to be a octal string, got [{mode}]")
    return mode


def valid_host_path_propagation(propagation: str):
    valid_propagations = ("shared", "slave", "private", "rshared", "rslave", "rprivate")
    if propagation not in valid_propagations:
        raise RenderError(f"Expected [propagation] to be one of [{', '.join(valid_propagations)}], got [{propagation}]")
    return propagation


def valid_portal_scheme_or_raise(scheme: str):
    schemes = ("http", "https")
    if scheme not in schemes:
        raise RenderError(f"Portal Scheme [{scheme}] is not valid. Valid options are: [{', '.join(schemes)}]")
    return scheme


def valid_port_or_raise(port: int):
    if port < 1 or port > 65535:
        raise RenderError(f"Invalid port [{port}]. Valid ports are between 1 and 65535")
    return port


def valid_ip_or_raise(ip: str):
    try:
        ipaddress.ip_address(ip)
    except ValueError:
        raise RenderError(f"Invalid IP address [{ip}]")
    return ip


def valid_port_mode_or_raise(mode: str):
    modes = ("ingress", "host")
    if mode not in modes:
        raise RenderError(f"Port Mode [{mode}] is not valid. Valid options are: [{', '.join(modes)}]")
    return mode


def valid_port_protocol_or_raise(protocol: str):
    protocols = ("tcp", "udp")
    if protocol not in protocols:
        raise RenderError(f"Port Protocol [{protocol}] is not valid. Valid options are: [{', '.join(protocols)}]")
    return protocol


def valid_depend_condition_or_raise(condition: str):
    valid_conditions = ("service_started", "service_healthy", "service_completed_successfully")
    if condition not in valid_conditions:
        raise RenderError(
            f"Depend Condition [{condition}] is not valid. Valid options are: [{', '.join(valid_conditions)}]"
        )
    return condition


def valid_cgroup_perm_or_raise(cgroup_perm: str):
    valid_cgroup_perms = ("r", "w", "m", "rw", "rm", "wm", "rwm", "")
    if cgroup_perm not in valid_cgroup_perms:
        raise RenderError(
            f"Cgroup Permission [{cgroup_perm}] is not valid. Valid options are: [{', '.join(valid_cgroup_perms)}]"
        )
    return cgroup_perm


def valid_cgroup_or_raise(cgroup: str):
    valid_cgroup = ("host", "private")
    if cgroup not in valid_cgroup:
        raise RenderError(f"Cgroup [{cgroup}] is not valid. Valid options are: [{', '.join(valid_cgroup)}]")
    return cgroup


def valid_device_cgroup_rule_or_raise(dev_grp_rule: str):
    parts = dev_grp_rule.split(" ")
    if len(parts) != 3:
        raise RenderError(
            f"Device Group Rule [{dev_grp_rule}] is not valid. Expected format is [<type> <major>:<minor> <permission>]"
        )

    valid_types = ("a", "b", "c")
    if parts[0] not in valid_types:
        raise RenderError(
            f"Device Group Rule [{dev_grp_rule}] is not valid. Expected type to be one of [{', '.join(valid_types)}]"
            f" but got [{parts[0]}]"
        )

    major, minor = parts[1].split(":")
    for part in (major, minor):
        if part != "*" and not part.isdigit():
            raise RenderError(
                f"Device Group Rule [{dev_grp_rule}] is not valid. Expected major and minor to be digits"
                f" or [*] but got [{major}] and [{minor}]"
            )

    valid_cgroup_perm_or_raise(parts[2])

    return dev_grp_rule


def allowed_dns_opt_or_raise(dns_opt: str):
    disallowed_dns_opts = []
    if dns_opt in disallowed_dns_opts:
        raise RenderError(f"DNS Option [{dns_opt}] is not allowed to added.")
    return dns_opt


def valid_http_path_or_raise(path: str):
    path = _valid_path_or_raise(path)
    return path


def valid_fs_path_or_raise(path: str):
    # There is no reason to allow / as a path,
    # either on host or in a container side.
    if path == "/":
        raise RenderError(f"Path [{path}] cannot be [/]")
    path = _valid_path_or_raise(path)
    return path


def is_allowed_path(input_path: str, is_ix_volume: bool = False) -> bool:
    """
    Validates that the given path (after resolving symlinks) is not
    one of the restricted paths or within those restricted directories.

    Returns True if the path is allowed, False otherwise.
    """
    # Resolve the path to avoid symlink bypasses
    real_path = Path(input_path).resolve()
    for restricted in RESTRICTED if not is_ix_volume else [r for r in RESTRICTED if r != Path("/mnt/.ix-apps")]:
        if real_path.is_relative_to(restricted):
            return False

    return real_path not in RESTRICTED_IN


def allowed_fs_host_path_or_raise(path: str, is_ix_volume: bool = False):
    if not is_allowed_path(path, is_ix_volume):
        raise RenderError(f"Path [{path}] is not allowed to be mounted.")
    return path


def _valid_path_or_raise(path: str):
    if path == "":
        raise RenderError(f"Path [{path}] cannot be empty")
    if not path.startswith("/"):
        raise RenderError(f"Path [{path}] must start with /")
    if "//" in path:
        raise RenderError(f"Path [{path}] cannot contain [//]")
    return path


def allowed_device_or_raise(path: str):
    disallowed_devices = ["/dev/dri", "/dev/kfd", "/dev/bus/usb", "/dev/snd", "/dev/net/tun"]
    if path in disallowed_devices:
        raise RenderError(f"Device [{path}] is not allowed to be manually added.")
    return path


def valid_network_mode_or_raise(mode: str, containers: list[str]):
    valid_modes = ("host", "none")
    if mode in valid_modes:
        return mode

    if mode.startswith("service:"):
        if mode[8:] not in containers:
            raise RenderError(f"Service [{mode[8:]}] not found")
        return mode

    raise RenderError(
        f"Invalid network mode [{mode}]. Valid options are: [{', '.join(valid_modes)}] or [service:<name>]"
    )


def valid_restart_policy_or_raise(policy: str, maximum_retry_count: int = 0):
    valid_restart_policies = ("always", "on-failure", "unless-stopped", "no")
    if policy not in valid_restart_policies:
        raise RenderError(
            f"Restart policy [{policy}] is not valid. Valid options are: [{', '.join(valid_restart_policies)}]"
        )
    if policy != "on-failure" and maximum_retry_count != 0:
        raise RenderError("Maximum retry count can only be set for [on-failure] restart policy")

    if maximum_retry_count < 0:
        raise RenderError("Maximum retry count must be a positive integer")

    return policy


def valid_cap_or_raise(cap: str):
    valid_policies = (
        "ALL",
        "AUDIT_CONTROL",
        "AUDIT_READ",
        "AUDIT_WRITE",
        "BLOCK_SUSPEND",
        "BPF",
        "CHECKPOINT_RESTORE",
        "CHOWN",
        "DAC_OVERRIDE",
        "DAC_READ_SEARCH",
        "FOWNER",
        "FSETID",
        "IPC_LOCK",
        "IPC_OWNER",
        "KILL",
        "LEASE",
        "LINUX_IMMUTABLE",
        "MAC_ADMIN",
        "MAC_OVERRIDE",
        "MKNOD",
        "NET_ADMIN",
        "NET_BIND_SERVICE",
        "NET_BROADCAST",
        "NET_RAW",
        "PERFMON",
        "SETFCAP",
        "SETGID",
        "SETPCAP",
        "SETUID",
        "SYS_ADMIN",
        "SYS_BOOT",
        "SYS_CHROOT",
        "SYS_MODULE",
        "SYS_NICE",
        "SYS_PACCT",
        "SYS_PTRACE",
        "SYS_RAWIO",
        "SYS_RESOURCE",
        "SYS_TIME",
        "SYS_TTY_CONFIG",
        "SYSLOG",
        "WAKE_ALARM",
    )

    if cap not in valid_policies:
        raise RenderError(f"Capability [{cap}] is not valid. " f"Valid options are: [{', '.join(valid_policies)}]")

    return cap
