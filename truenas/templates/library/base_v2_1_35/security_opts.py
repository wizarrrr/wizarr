from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from render import Render

try:
    from .error import RenderError
    from .validations import valid_security_opt_or_raise
except ImportError:
    from error import RenderError
    from validations import valid_security_opt_or_raise


class SecurityOpt:
    def __init__(self, opt: str, value: str | bool | None = None, arg: str | None = None):
        self._opt: str = valid_security_opt_or_raise(opt)
        self._value = str(value).lower() if isinstance(value, bool) else value
        self._arg: str | None = arg

    def render(self):
        result = self._opt
        if self._value is not None:
            result = f"{result}={self._value}"
        if self._arg is not None:
            result = f"{result}:{self._arg}"
        return result


class SecurityOpts:
    def __init__(self, render_instance: "Render"):
        self._render_instance = render_instance
        self._opts: dict[str, SecurityOpt] = dict()
        self.add_opt("no-new-privileges", True)

    def add_opt(self, key: str, value: str | bool | None, arg: str | None = None):
        if key in self._opts:
            raise RenderError(f"Security Option [{key}] already added")
        self._opts[key] = SecurityOpt(key, value, arg)

    def remove_opt(self, key: str):
        if key not in self._opts:
            raise RenderError(f"Security Option [{key}] not found")
        del self._opts[key]

    def has_opts(self):
        return len(self._opts) > 0

    def render(self):
        result = []
        for opt in sorted(self._opts.values(), key=lambda o: o._opt):
            result.append(opt.render())
        return result
