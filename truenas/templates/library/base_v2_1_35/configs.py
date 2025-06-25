from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from render import Render

try:
    from .error import RenderError
    from .formatter import escape_dollar
    from .validations import valid_octal_mode_or_raise, valid_fs_path_or_raise
except ImportError:
    from error import RenderError
    from formatter import escape_dollar
    from validations import valid_octal_mode_or_raise, valid_fs_path_or_raise


class Configs:
    def __init__(self, render_instance: "Render"):
        self._render_instance = render_instance
        self._configs: dict[str, dict] = {}

    def add(self, name: str, data: str):
        if not isinstance(data, str):
            raise RenderError(f"Expected [data] to be a string, got [{type(data)}]")

        if name not in self._configs:
            self._configs[name] = {"name": name, "data": data}
            return

        if data == self._configs[name]["data"]:
            return

        raise RenderError(f"Config [{name}] already added with different data")

    def has_configs(self):
        return bool(self._configs)

    def render(self):
        return {
            c["name"]: {"content": escape_dollar(c["data"])}
            for c in sorted(self._configs.values(), key=lambda c: c["name"])
        }


class ContainerConfigs:
    def __init__(self, render_instance: "Render", configs: Configs):
        self._render_instance = render_instance
        self.top_level_configs: Configs = configs
        self.container_configs: set[ContainerConfig] = set()

    def add(self, name: str, data: str, target: str, mode: str = ""):
        self.top_level_configs.add(name, data)

        if target == "":
            raise RenderError(f"Expected [target] to be set for config [{name}]")
        if mode != "":
            mode = valid_octal_mode_or_raise(mode)

        if target in [c.target for c in self.container_configs]:
            raise RenderError(f"Target [{target}] already used for another config")
        target = valid_fs_path_or_raise(target)
        self.container_configs.add(ContainerConfig(self._render_instance, name, target, mode))

    def has_configs(self):
        return bool(self.container_configs)

    def render(self):
        return [c.render() for c in sorted(self.container_configs, key=lambda c: c.source)]


class ContainerConfig:
    def __init__(self, render_instance: "Render", source: str, target: str, mode: str):
        self._render_instance = render_instance
        self.source = source
        self.target = target
        self.mode = mode

    def render(self):
        result: dict[str, str | int] = {
            "source": self.source,
            "target": self.target,
        }

        if self.mode:
            result["mode"] = int(self.mode, 8)

        return result
