"""Extract translation calls from wizard Markdown files."""

import ast
import re
from collections.abc import Generator, Iterable
from typing import Any, BinaryIO

TRANSLATION_CALL = re.compile(r"(?<![A-Za-z0-9_])(?P<name>_l|_)\s*\(")


def _skip_space(source: str, position: int) -> int:
    while position < len(source) and source[position].isspace():
        position += 1
    return position


def _read_string(source: str, position: int) -> tuple[str, int] | None:
    if position >= len(source) or source[position] not in {"'", '"'}:
        return None

    quote = source[position]
    end = position + 1
    while end < len(source):
        if source[end] == "\\":
            end += 2
            continue
        if source[end] == quote:
            literal = source[position : end + 1]
            try:
                value = ast.literal_eval(literal)
            except (SyntaxError, ValueError):
                return None
            return (value, end + 1) if isinstance(value, str) else None
        end += 1

    return None


def _read_message(source: str, position: int) -> tuple[str, int] | None:
    parts: list[str] = []
    position = _skip_space(source, position)

    while parsed := _read_string(source, position):
        part, position = parsed
        parts.append(part)
        position = _skip_space(source, position)

    if not parts or position >= len(source) or source[position] != ")":
        return None
    return "".join(parts), position + 1


def extract_wizard_markdown(
    fileobj: BinaryIO,
    keywords: Iterable[str],
    comment_tags: Iterable[str],  # noqa: ARG001
    options: dict[str, Any],  # noqa: ARG001
) -> Generator[tuple[int, str, str, list[str]]]:
    """Yield messages without parsing Wizarr widget syntax as Jinja."""
    source = fileobj.read().decode("utf-8")
    enabled_keywords = set(keywords)

    for match in TRANSLATION_CALL.finditer(source):
        function_name = match.group("name")
        if function_name not in enabled_keywords:
            continue

        parsed = _read_message(source, match.end())
        if parsed is None:
            continue

        message, _end = parsed
        line_number = source.count("\n", 0, match.start()) + 1
        yield line_number, function_name, message, []
