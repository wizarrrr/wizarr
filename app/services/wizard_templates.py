"""Render stored templates in a sandbox without access to the application."""

import re
from contextvars import ContextVar
from typing import Any

from flask import url_for
from flask_babel import get_translations, gettext
from jinja2 import nodes
from jinja2.exceptions import SecurityError
from jinja2.filters import do_format
from jinja2.sandbox import ImmutableSandboxedEnvironment

MAX_TEMPLATE_LENGTH = 100_000
MAX_OUTPUT_LENGTH = 1_000_000
# Loop iterations and function calls in one render.
MAX_STEPS = 100_000
MAX_REPEAT_LENGTH = 10_000
MAX_FORMAT_WIDTH = 1_000
# Settings with these names can hold credentials. Do not show them to invited users.
SECRET_NAME = re.compile(
    r"password|passwd|secret|token|credential|cookie|session|private|api_?key|(^|_)key$",
    re.IGNORECASE,
)
_PRIMITIVES = (str, int, float, bool, type(None))
_FORMAT_SIZE = re.compile(r"%(?:\([^)]*\))?[-#0 +]*(\*|\d+)?(?:\.(\*|\d+))?")
_LOOP_FILTER = "wizard_loop_guard"
_steps_left: ContextVar[list[int]] = ContextVar("wizard_template_steps")


def wizard_context(context: dict | None = None) -> dict:
    """Copy text and number values. Do not pass credentials or application objects."""
    values = {
        key: value
        for key, value in (context or {}).items()
        if isinstance(key, str)
        and type(value) in _PRIMITIVES
        and not SECRET_NAME.search(key)
    }
    return {**values, "settings": values}


def _use_step() -> None:
    steps = _steps_left.get()
    steps[0] -= 1
    if steps[0] < 0:
        raise SecurityError("Wizard template does too much work.")


def _loop_guard(iterable):
    for item in iterable:
        _use_step()
        yield item


def _check_format(text: str) -> None:
    """Stop format strings that pad a value to a very large size."""
    for match in _FORMAT_SIZE.finditer(text):
        for size in match.groups():
            if size == "*" or (
                size and (len(size) > 4 or int(size) > MAX_FORMAT_WIDTH)
            ):
                raise SecurityError("Wizard template pads text too much.")


def _translate(message: str, **variables) -> str:
    """Translate a message. Format it with keyword values, like Flask-Babel."""
    if not isinstance(message, str):
        raise SecurityError("Translation requires text.")
    text = gettext(message)
    if not variables:
        return text
    _check_format(text)
    return text % variables


def _gettext(message: str) -> str:
    """Translate a message for Jinja's i18n extension. Jinja formats it."""
    text = _translate(message)
    _check_format(text)
    return text


def _ngettext(singular: str, plural: str, num: int) -> str:
    """Translate a plural message for Jinja's i18n extension. Jinja formats it."""
    text = get_translations().ungettext(singular, plural, num)
    _check_format(text)
    return text


def _format(value, *args, **kwargs) -> str:
    """Apply the format filter with the same size check as the % operator."""
    _check_format(str(value))
    return do_format(value, *args, **kwargs)


class _WizardEnvironment(ImmutableSandboxedEnvironment):
    globals: dict[str, Any]
    intercepted_binops = frozenset({"*", "**", "%"})

    # Jinja names the first argument __self, so templates can pass `self=`.
    def call(__self, __context, __obj, *args, **kwargs):
        _use_step()
        return super().call(__context, __obj, *args, **kwargs)

    def call_binop(self, context, operator, left, right):
        if operator == "**":
            raise SecurityError("This operation is not available in wizard templates.")
        if operator == "*":
            for sequence, count in ((left, right), (right, left)):
                if (
                    isinstance(sequence, (str, list, tuple))
                    and isinstance(count, int)
                    and len(sequence) * count > MAX_REPEAT_LENGTH
                ):
                    raise SecurityError("Wizard template repeats text too much.")
        if operator == "%" and isinstance(left, str):
            _check_format(left)
        return super().call_binop(context, operator, left, right)


_ENV = _WizardEnvironment(autoescape=False, extensions=["jinja2.ext.i18n"])
_ENV.install_gettext_callables(_gettext, _ngettext, newstyle=True)  # type: ignore
# Keep Flask-Babel's `_`: it formats a message only when it gets keyword values.
_ENV.globals["_"] = _translate
_ENV.globals["url_for"] = url_for
_ENV.globals["min"] = min
_ENV.globals["max"] = max
# lipsum can create very large text.
_ENV.globals.pop("lipsum", None)
_ENV.filters["format"] = _format
_ENV.filters[_LOOP_FILTER] = _loop_guard


def _guard_loops(tree: nodes.Template) -> None:
    """Count each loop iteration against the render budget."""
    for loop in list(tree.find_all(nodes.For)):
        if loop.recursive:
            raise SecurityError(
                "Recursive loops are not available in wizard templates."
            )
        loop.iter = nodes.Filter(
            loop.iter, _LOOP_FILTER, [], [], None, None, lineno=loop.lineno
        )


def render_wizard_template(source: str, context: dict | None = None) -> str:
    """Render a stored template in the sandbox with public display values."""
    if len(source) > MAX_TEMPLATE_LENGTH:
        raise SecurityError("Wizard template is too large.")
    tree = _ENV.parse(source)
    # Stored templates cannot load other templates.
    if next(
        tree.find_all((nodes.Import, nodes.FromImport, nodes.Include, nodes.Extends)),
        None,
    ):
        raise SecurityError("This statement is not available in wizard templates.")
    _guard_loops(tree)
    template = _ENV.from_string(tree)
    steps = _steps_left.set([MAX_STEPS])
    try:
        chunks = []
        length = 0
        for chunk in template.generate(**wizard_context(context)):
            length += len(chunk)
            if length > MAX_OUTPUT_LENGTH:
                raise SecurityError("Wizard output is too large.")
            chunks.append(chunk)
        return "".join(chunks)
    finally:
        _steps_left.reset(steps)
