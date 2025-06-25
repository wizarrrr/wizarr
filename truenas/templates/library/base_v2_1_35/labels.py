from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from render import Render

try:
    from .error import RenderError
    from .formatter import escape_dollar
except ImportError:
    from error import RenderError
    from formatter import escape_dollar


class Labels:
    def __init__(self, render_instance: "Render"):
        self._render_instance = render_instance
        self._labels: dict[str, str] = {}

    def add_label(self, key: str, value: str):
        if not key:
            raise RenderError("Labels must have a key")

        if key.startswith("com.docker.compose"):
            raise RenderError(f"Label [{key}] cannot start with [com.docker.compose] as it is reserved")

        if key in self._labels.keys():
            raise RenderError(f"Label [{key}] already added")

        self._labels[key] = escape_dollar(str(value))

    def has_labels(self) -> bool:
        return bool(self._labels)

    def render(self) -> dict[str, str]:
        if not self.has_labels():
            return {}
        return {label: value for label, value in sorted(self._labels.items())}
