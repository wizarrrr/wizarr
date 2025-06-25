from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from render import Render
try:
    from .error import RenderError
    from .formatter import escape_dollar
    from .resources import Resources
except ImportError:
    from error import RenderError
    from formatter import escape_dollar
    from resources import Resources


class Environment:
    def __init__(self, render_instance: "Render", resources: Resources):
        self._render_instance = render_instance
        self._resources = resources
        # Stores variables that user defined
        self._user_vars: dict[str, Any] = {}
        # Stores variables that are automatically added (based on values)
        self._auto_variables: dict[str, Any] = {}
        # Stores variables that are added by the application developer
        self._app_dev_variables: dict[str, Any] = {}

        self._skip_generic_variables: bool = render_instance.values.get("skip_generic_variables", False)

        self._auto_add_variables_from_values()

    def _auto_add_variables_from_values(self):
        if not self._skip_generic_variables:
            self._add_generic_variables()
        self._add_nvidia_variables()

    def _add_generic_variables(self):
        self._auto_variables["TZ"] = self._render_instance.values.get("TZ", "Etc/UTC")
        self._auto_variables["UMASK"] = self._render_instance.values.get("UMASK", "002")
        self._auto_variables["UMASK_SET"] = self._render_instance.values.get("UMASK", "002")

        run_as = self._render_instance.values.get("run_as", {})
        user = run_as.get("user")
        group = run_as.get("group")
        if user:
            self._auto_variables["PUID"] = user
            self._auto_variables["UID"] = user
            self._auto_variables["USER_ID"] = user
        if group:
            self._auto_variables["PGID"] = group
            self._auto_variables["GID"] = group
            self._auto_variables["GROUP_ID"] = group

    def _add_nvidia_variables(self):
        if self._resources._nvidia_ids:
            self._auto_variables["NVIDIA_DRIVER_CAPABILITIES"] = "all"
            self._auto_variables["NVIDIA_VISIBLE_DEVICES"] = ",".join(sorted(self._resources._nvidia_ids))
        else:
            self._auto_variables["NVIDIA_VISIBLE_DEVICES"] = "void"

    def _format_value(self, v: Any) -> str:
        value = str(v)

        # str(bool) returns "True" or "False",
        # but we want "true" or "false"
        if isinstance(v, bool):
            value = value.lower()
        return value

    def add_env(self, name: str, value: Any):
        if not name:
            raise RenderError(f"Environment variable name cannot be empty. [{name}]")
        if name in self._app_dev_variables.keys():
            raise RenderError(
                f"Found duplicate environment variable [{name}] in application developer environment variables."
            )
        self._app_dev_variables[name] = value

    def add_user_envs(self, user_env: list[dict]):
        for item in user_env:
            if not item.get("name"):
                raise RenderError(f"Environment variable name cannot be empty. [{item}]")
            if item["name"] in self._user_vars.keys():
                raise RenderError(
                    f"Found duplicate environment variable [{item['name']}] in user environment variables."
                )
            self._user_vars[item["name"]] = item.get("value")

    def has_variables(self):
        return len(self._auto_variables) > 0 or len(self._user_vars) > 0 or len(self._app_dev_variables) > 0

    def render(self):
        result: dict[str, str] = {}

        # Add envs from auto variables
        result.update({k: self._format_value(v) for k, v in self._auto_variables.items()})

        # Track defined keys for faster lookup
        defined_keys = set(result.keys())

        # Add envs from application developer (prohibit overwriting auto variables)
        for k, v in self._app_dev_variables.items():
            if k in defined_keys:
                raise RenderError(f"Environment variable [{k}] is already defined automatically from the library.")
            result[k] = self._format_value(v)
            defined_keys.add(k)

        # Add envs from user (prohibit overwriting app developer envs and auto variables)
        for k, v in self._user_vars.items():
            if k in defined_keys:
                raise RenderError(f"Environment variable [{k}] is already defined from the application developer.")
            result[k] = self._format_value(v)

        return {k: escape_dollar(v) for k, v in result.items()}
