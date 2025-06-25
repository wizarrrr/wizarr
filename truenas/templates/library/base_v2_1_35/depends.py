from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from render import Render

try:
    from .error import RenderError
    from .validations import valid_depend_condition_or_raise
except ImportError:
    from error import RenderError
    from validations import valid_depend_condition_or_raise


class Depends:
    def __init__(self, render_instance: "Render"):
        self._render_instance = render_instance
        self._dependencies: dict[str, str] = {}

    def add_dependency(self, name: str, condition: str):
        condition = valid_depend_condition_or_raise(condition)
        if name in self._dependencies.keys():
            raise RenderError(f"Dependency [{name}] already added")
        if name not in self._render_instance.container_names():
            raise RenderError(
                f"Dependency [{name}] not found in defined containers. "
                f"Available containers: [{', '.join(self._render_instance.container_names())}]"
            )
        self._dependencies[name] = condition

    def has_dependencies(self):
        return len(self._dependencies) > 0

    def render(self):
        return {d: {"condition": c} for d, c in self._dependencies.items()}
