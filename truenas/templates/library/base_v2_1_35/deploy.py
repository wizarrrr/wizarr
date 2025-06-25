from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from render import Render

try:
    from .resources import Resources
except ImportError:
    from resources import Resources


class Deploy:
    def __init__(self, render_instance: "Render"):
        self._render_instance = render_instance
        self.resources: Resources = Resources(self._render_instance)

    def has_deploy(self):
        return self.resources.has_resources()

    def render(self):
        if self.resources.has_resources():
            return {"resources": self.resources.render()}

        return {}
