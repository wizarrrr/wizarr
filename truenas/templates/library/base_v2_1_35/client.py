import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from render import Render

try:
    from .error import RenderError
except ImportError:
    from error import RenderError


def is_truenas_system():
    """Check if we're running on a TrueNAS system"""
    return "truenas" in os.uname().release


# Import based on system detection
if is_truenas_system():
    from truenas_api_client import Client as TrueNASClient

    try:
        # 25.04 and later
        from truenas_api_client.exc import ValidationErrors
    except ImportError:
        # 24.10 and earlier
        from truenas_api_client import ValidationErrors
else:
    # Mock classes for non-TrueNAS systems
    class TrueNASClient:
        def call(self, *args, **kwargs):
            return None

    class ValidationErrors(Exception):
        def __init__(self, errors):
            self.errors = errors


class Client:
    def __init__(self, render_instance: "Render"):
        self.client = TrueNASClient()
        self._render_instance = render_instance
        self._app_name: str = self._render_instance.values.get("ix_context", {}).get("app_name", "") or "unknown"

    def validate_ip_port_combo(self, ip: str, port: int) -> None:
        # Example of an error messages:
        # The port is being used by following services: 1) "0.0.0.0:80" used by WebUI Service
        # The port is being used by following services: 1) "0.0.0.0:9998" used by Applications ('$app_name' application)
        try:
            self.client.call("port.validate_port", f"render.{self._app_name}.schema", port, ip, None, True)
        except ValidationErrors as e:
            err_str = str(e)
            # If the IP:port combo appears more than once in the error message,
            # means that the port is used by more than one service/app.
            # This shouldn't happen in a well-configured system.
            # Notice that the ip portion is not included check,
            # because input might be a specific IP, but another service or app
            # might be using the same port on a wildcard IP
            if err_str.count(f':{port}" used by') > 1:
                raise RenderError(err_str) from None

            # If the error complains about the current app, we ignore it
            # This is to handle cases where the app is being updated or edited
            if f"Applications ('{self._app_name}' application)" in err_str:
                # During upgrade, we want to ignore the error if it is related to the current app
                return

            raise RenderError(err_str) from None
        except Exception:
            pass
