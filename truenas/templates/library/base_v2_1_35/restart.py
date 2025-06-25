from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from render import Render

try:
    from .validations import valid_restart_policy_or_raise
except ImportError:
    from validations import valid_restart_policy_or_raise


class RestartPolicy:
    def __init__(self, render_instance: "Render"):
        self._render_instance = render_instance
        self._policy: str = "unless-stopped"
        self._maximum_retry_count: int = 0

    def set_policy(self, policy: str, maximum_retry_count: int = 0):
        self._policy = valid_restart_policy_or_raise(policy, maximum_retry_count)
        self._maximum_retry_count = maximum_retry_count

    def render(self):
        if self._policy == "on-failure" and self._maximum_retry_count > 0:
            return f"{self._policy}:{self._maximum_retry_count}"
        return self._policy
