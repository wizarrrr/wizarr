"""Render stored templates without access to the application environment."""

from typing import Any

from flask_babel import gettext
from jinja2 import nodes
from jinja2.exceptions import SecurityError
from jinja2.sandbox import ImmutableSandboxedEnvironment

MAX_TEMPLATE_LENGTH = 100_000
MAX_OUTPUT_LENGTH = 1_000_000
DISPLAY_KEYS = frozenset({"server_name", "server_type", "server_url", "external_url"})


def wizard_context(context: dict | None = None) -> dict:
    """Copy only public display values. Do not pass application objects."""
    context = context or {}
    values = {
        key: value
        for key in DISPLAY_KEYS
        if type(value := context.get(key)) in (str, int, float, bool, type(None))
    }
    return {**values, "settings": values}


def _translate(message: str) -> str:
    """Translate one message with the active locale."""
    if not isinstance(message, str):
        raise SecurityError("Translation requires text.")
    return gettext(message)


class _WizardEnvironment(ImmutableSandboxedEnvironment):
    globals: dict[str, Any]
    intercepted_binops = frozenset({"*", "**", "%"})

    def is_safe_attribute(self, obj, attr, value):  # noqa: ARG002  # Jinja override.
        # Dictionary keys still work through Jinja's item lookup.
        return False

    def is_safe_callable(self, obj):
        return obj is _translate

    def call_binop(self, context, operator, left, right):
        if operator == "**" or not all(
            type(value) in (int, float) for value in (left, right)
        ):
            raise SecurityError("This operation is not available in wizard templates.")
        return super().call_binop(context, operator, left, right)


_ENV = _WizardEnvironment(autoescape=False)  # Escape titles and sanitize final HTML.
_ENV.globals = {"_": _translate}
_ENV.filters = {
    key: value
    for key, value in _ENV.filters.items()
    if key
    in {
        "default",
        "d",
        "escape",
        "e",
        "upper",
        "lower",
        "title",
        "trim",
        "capitalize",
        "length",
        "urlencode",
    }
}
_ENV.tests = {
    key: value
    for key, value in _ENV.tests.items()
    if key
    in {
        "defined",
        "undefined",
        "none",
        "boolean",
        "true",
        "false",
        "string",
        "number",
        "equalto",
        "eq",
        "ne",
    }
}


def render_wizard_template(source: str, context: dict | None = None) -> str:
    """Render display expressions and conditions in a restricted environment."""
    if len(source) > MAX_TEMPLATE_LENGTH:
        raise SecurityError("Wizard template is too large.")
    tree = _ENV.parse(source)
    # Loops, assignments and macros can consume unbounded resources.
    forbidden = (
        nodes.For,
        nodes.Macro,
        nodes.CallBlock,
        nodes.Assign,
        nodes.AssignBlock,
        nodes.With,
        nodes.Import,
        nodes.FromImport,
        nodes.Include,
        nodes.Extends,
        nodes.Block,
    )
    if next(tree.find_all(forbidden), None) is not None:
        raise SecurityError("This statement is not available in wizard templates.")
    template = _ENV.from_string(tree)
    chunks = []
    length = 0
    for chunk in template.generate(**wizard_context(context)):
        length += len(chunk)
        if length > MAX_OUTPUT_LENGTH:
            raise SecurityError("Wizard output is too large.")
        chunks.append(chunk)
    return "".join(chunks)
