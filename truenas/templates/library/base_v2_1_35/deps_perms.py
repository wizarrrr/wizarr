import json
import pathlib
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from render import Render
    from storage import IxStorage

try:
    from .error import RenderError
    from .validations import valid_octal_mode_or_raise, valid_fs_path_or_raise
except ImportError:
    from error import RenderError
    from validations import valid_octal_mode_or_raise, valid_fs_path_or_raise


class PermsContainer:
    def __init__(self, render_instance: "Render", name: str):
        self._render_instance = render_instance
        self._name = name
        self.actions: set[str] = set()
        self.parsed_configs: list[dict] = []

    def add_or_skip_action(self, identifier: str, volume_config: "IxStorage", action_config: dict):
        identifier = self.normalize_identifier_for_path(identifier)
        if identifier in self.actions:
            raise RenderError(f"Action with id [{identifier}] already used for another permission action")

        parsed_action = self.parse_action(identifier, volume_config, action_config)
        if parsed_action:
            self.parsed_configs.append(parsed_action)
            self.actions.add(identifier)

    def parse_action(self, identifier: str, volume_config: "IxStorage", action_config: dict):
        valid_modes = [
            "always",  # Always set permissions, without checking.
            "check",  # Checks if permissions are correct, and set them if not.
        ]
        mode = action_config.get("mode", "check")
        uid = action_config.get("uid", None)
        gid = action_config.get("gid", None)
        chmod = action_config.get("chmod", None)
        recursive = action_config.get("recursive", False)
        mount_path = pathlib.Path("/mnt/permission", identifier).as_posix()
        is_temporary = False

        vol_type = volume_config.get("type", "")
        match vol_type:
            case "temporary":
                # If it is a temporary volume, we force auto permissions
                # and set is_temporary to True, so it will be cleaned up
                is_temporary = True
                recursive = True
            case "volume":
                if not volume_config.get("volume_config", {}).get("auto_permissions", False):
                    return None
            case "host_path":
                host_path_config = volume_config.get("host_path_config", {})
                # Skip when ACL enabled
                if host_path_config.get("acl_enable", False):
                    return None
                if not host_path_config.get("auto_permissions", False):
                    return None
            case "ix_volume":
                ix_vol_config = volume_config.get("ix_volume_config", {})
                # Skip when ACL enabled
                if ix_vol_config.get("acl_enable", False):
                    return None
                # For ix_volumes, we default to auto_permissions = True
                if not ix_vol_config.get("auto_permissions", True):
                    return None
            case _:
                # Skip for other types
                return None

        if mode not in valid_modes:
            raise RenderError(f"Expected [mode] to be one of [{', '.join(valid_modes)}], got [{mode}]")
        if not isinstance(uid, int) or not isinstance(gid, int):
            raise RenderError("Expected [uid] and [gid] to be set when [auto_permissions] is enabled")
        if chmod is not None:
            chmod = valid_octal_mode_or_raise(chmod)

        mount_path = valid_fs_path_or_raise(mount_path)
        return {
            "mount_path": mount_path,
            "volume_config": volume_config,
            "action_data": {
                "mount_path": mount_path,
                "is_temporary": is_temporary,
                "identifier": identifier,
                "recursive": recursive,
                "mode": mode,
                "uid": uid,
                "gid": gid,
                "chmod": chmod,
            },
        }

    def normalize_identifier_for_path(self, identifier: str):
        return identifier.rstrip("/").lstrip("/").lower().replace("/", "_").replace(".", "-").replace(" ", "-")

    def has_actions(self):
        return bool(self.actions)

    def activate(self):
        if len(self.parsed_configs) != len(self.actions):
            raise RenderError("Number of actions and parsed configs does not match")

        if not self.has_actions():
            raise RenderError("No actions added. Check if there are actions before activating")

        # Add the container and set it up
        c = self._render_instance.add_container(self._name, "python_permissions_image")
        c.set_user(0, 0)
        c.add_caps(["CHOWN", "FOWNER", "DAC_OVERRIDE"])
        c.set_network_mode("none")

        # Don't attach any devices
        c.remove_devices()

        c.deploy.resources.set_profile("medium")
        c.restart.set_policy("on-failure", maximum_retry_count=1)
        c.healthcheck.disable()

        c.set_entrypoint(["python3", "/script/run.py"])
        script = "#!/usr/bin/env python3\n"
        script += get_script()
        c.configs.add("permissions_run_script", script, "/script/run.py", "0700")

        actions_data: list[dict] = []
        for parsed in self.parsed_configs:
            c.add_storage(parsed["mount_path"], parsed["volume_config"])
            actions_data.append(parsed["action_data"])

        actions_data_json = json.dumps(actions_data)
        c.configs.add("permissions_actions_data", actions_data_json, "/script/actions.json", "0500")


def get_script():
    return """
import os
import json
import time
import shutil

with open("/script/actions.json", "r") as f:
    actions_data = json.load(f)

if not actions_data:
    # If this script is called, there should be actions data
    raise ValueError("No actions data found")

def fix_perms(path, chmod, recursive=False):
    print(f"Changing permissions{' recursively ' if recursive else ' '}to {chmod} on: [{path}]")
    os.chmod(path, int(chmod, 8))
    if recursive:
        for root, dirs, files in os.walk(path):
            for f in files:
                os.chmod(os.path.join(root, f), int(chmod, 8))
    print("Permissions after changes:")
    print_chmod_stat()

def fix_owner(path, uid, gid, recursive=False):
    print(f"Changing ownership{' recursively ' if recursive else ' '}to {uid}:{gid} on: [{path}]")
    os.chown(path, uid, gid)
    if recursive:
        for root, dirs, files in os.walk(path):
            for f in files:
                os.chown(os.path.join(root, f), uid, gid)
    print("Ownership after changes:")
    print_chown_stat()

def print_chown_stat():
    curr_stat = os.stat(action["mount_path"])
    print(f"Ownership: [{curr_stat.st_uid}:{curr_stat.st_gid}]")

def print_chmod_stat():
    curr_stat = os.stat(action["mount_path"])
    print(f"Permissions: [{oct(curr_stat.st_mode)[3:]}]")

def print_chown_diff(curr_stat, uid, gid):
    print(f"Ownership: wanted [{uid}:{gid}], got [{curr_stat.st_uid}:{curr_stat.st_gid}].")

def print_chmod_diff(curr_stat, mode):
    print(f"Permissions: wanted [{mode}], got [{oct(curr_stat.st_mode)[3:]}].")

def perform_action(action):
    start_time = time.time()
    print(f"=== Applying configuration on volume with identifier [{action['identifier']}] ===")

    if not os.path.isdir(action["mount_path"]):
        print(f"Path [{action['mount_path']}] is not a directory, skipping...")
        return

    if action["is_temporary"]:
        print(f"Path [{action['mount_path']}] is a temporary directory, ensuring it is empty...")
        for item in os.listdir(action["mount_path"]):
            item_path = os.path.join(action["mount_path"], item)

            # Exclude the safe directory, where we can use to mount files temporarily
            if os.path.basename(item_path) == "ix-safe":
                continue
            if os.path.isdir(item_path):
                shutil.rmtree(item_path)
            else:
                os.remove(item_path)

    if not action["is_temporary"] and os.listdir(action["mount_path"]):
        print(f"Path [{action['mount_path']}] is not empty, skipping...")
        return

    print(f"Current Ownership and Permissions on [{action['mount_path']}]:")
    curr_stat = os.stat(action["mount_path"])
    print_chown_diff(curr_stat, action["uid"], action["gid"])
    print_chmod_diff(curr_stat, action["chmod"])
    print("---")

    if action["mode"] == "always":
        fix_owner(action["mount_path"], action["uid"], action["gid"], action["recursive"])
        if not action["chmod"]:
            print("Skipping permissions check, chmod is falsy")
        else:
            fix_perms(action["mount_path"], action["chmod"], action["recursive"])
        return

    elif action["mode"] == "check":
        if curr_stat.st_uid != action["uid"] or curr_stat.st_gid != action["gid"]:
            print("Ownership is incorrect. Fixing...")
            fix_owner(action["mount_path"], action["uid"], action["gid"], action["recursive"])
        else:
            print("Ownership is correct. Skipping...")

        if not action["chmod"]:
            print("Skipping permissions check, chmod is falsy")
        else:
            if oct(curr_stat.st_mode)[3:] != action["chmod"]:
                print("Permissions are incorrect. Fixing...")
                fix_perms(action["mount_path"], action["chmod"], action["recursive"])
            else:
                print("Permissions are correct. Skipping...")

    print(f"Time taken: {(time.time() - start_time) * 1000:.2f}ms")
    print(f"=== Finished applying configuration on volume with identifier [{action['identifier']}] ==")
    print()

if __name__ == "__main__":
    start_time = time.time()
    for action in actions_data:
        perform_action(action)
    print(f"Total time taken: {(time.time() - start_time) * 1000:.2f}ms")
"""
