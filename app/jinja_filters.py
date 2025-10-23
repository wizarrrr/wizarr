import contextlib
import logging
import os
import time
from datetime import UTC, datetime

from markupsafe import Markup, escape

try:
    from zoneinfo import ZoneInfo
except (
    ImportError
):  # pragma: no cover - Python <3.9 not officially supported but handle gracefully
    ZoneInfo = None  # type: ignore[assignment]

# Mapping of server types to their desired pastel background colours
_SERVER_TAG_COLOURS = {
    "emby": "#77DD77",  # soft green
    "plex": "#FDFD96",  # pale yellow
    "jellyfin": "#DAB1DA",  # light lavender
    "audiobookshelf": "#E9C9AA",  # peach
    "abs": "#E9C9AA",  # alias for Audiobookshelf (ABS)
    "romm": "#C3B1E1",  # light purple
}

_DEFAULT_COLOUR = "#E0E0E0"  # neutral grey fallback


def _resolve_local_timezone():
    """Determine the timezone to use for rendering timestamps."""
    tz_name = os.environ.get("TZ")

    if tz_name and hasattr(time, "tzset"):
        with contextlib.suppress(Exception):
            time.tzset()

    if ZoneInfo is not None:
        # First try explicit TZ environment variable
        if tz_name:
            try:
                return ZoneInfo(tz_name)
            except Exception as exc:
                logging.debug(f"Failed to load timezone {tz_name}: {exc}")

        # Fall back to system tzname if available
        try:
            local_name = time.tzname[0] if time.tzname else None
            if local_name:
                return ZoneInfo(local_name)
        except Exception as exc:
            logging.debug(f"Failed to load system timezone {local_name}: {exc}")

    # Fallback: use the system local timezone as determined by datetime
    try:
        return datetime.now().astimezone().tzinfo
    except Exception:
        return None


_LOCAL_TIMEZONE = _resolve_local_timezone()


def _server_colour(server_type: str) -> str:
    """Return the hex colour for the given *server_type* or a default grey."""
    if not server_type:
        return _DEFAULT_COLOUR
    return _SERVER_TAG_COLOURS.get(server_type.lower(), _DEFAULT_COLOUR)


def server_type_tag(server_type: str) -> Markup:
    """Return a ready-to-use <span> tag for the *server_type* with consistent colours.

    The tag renders with Tailwind utility spacing classes so it still fits nicely
    in existing layouts, while the background colour is controlled inline to
    guarantee the exact palette requested by design.
    """
    colour = _server_colour(server_type)
    # Always use black text for better contrast on these pastel backgrounds.
    text = escape(server_type.title() if server_type else "Unknown")
    html = (
        f'<span class="text-xs inline-block font-medium px-2 py-0.5 rounded-lg" '
        f'style="background-color: {colour}; color: #000;">{text}</span>'
    )
    return Markup(html)  # noqa: S704  # User input is escaped, colour from safe dict


def server_name_tag(server_type: str, server_name: str) -> Markup:
    """Return a ready-to-use <span> tag with custom text but server_type colours.

    Uses the server_type for determining the background colour but displays
    the server_name as the text content.
    """
    colour = _server_colour(server_type)
    # Always use black text for better contrast on these pastel backgrounds.
    text = escape(server_name if server_name else "Unknown")
    html = (
        f'<span class="text-xs inline-block font-medium px-2 py-0.5 rounded-lg" '
        f'style="background-color: {colour}; color: #000;">{text}</span>'
    )
    return Markup(html)  # noqa: S704  # User input is escaped, colour from safe dict


def human_date(date_value) -> str:
    """Format date to 'Jan 15, 2024 at 2:30 PM'."""
    if not date_value:
        return "—"

    # Handle string datetime values (ISO format)
    if isinstance(date_value, str):
        try:
            # Parse common ISO formats
            for fmt in [
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d %H:%M",
                "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%dT%H:%M:%S.%f",
            ]:
                try:
                    date_value = datetime.strptime(date_value, fmt).replace(tzinfo=UTC)
                    break
                except ValueError:
                    continue
            else:
                # If we can't parse it, just return the original truncated string
                return date_value[:16] if len(date_value) > 16 else date_value
        except (ValueError, AttributeError):
            return date_value[:16] if len(date_value) > 16 else date_value

    # Handle datetime objects
    if hasattr(date_value, "strftime"):
        return date_value.strftime("%b %-d, %Y at %-I:%M %p")

    # Fallback for unknown types
    return str(date_value)[:16]


def local_date(date_value, format_str="%m/%d %H:%M") -> str:
    """Convert UTC datetime to local timezone."""
    if not date_value:
        return "—"

    # Parse string to datetime if needed
    if isinstance(date_value, str):
        for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S"]:
            with contextlib.suppress(ValueError):
                date_value = datetime.strptime(date_value.rstrip("Z"), fmt).replace(
                    tzinfo=UTC
                )
                break
        else:
            return str(date_value)[:16]

    # Format datetime object
    if hasattr(date_value, "strftime"):
        if date_value.tzinfo is None:
            date_value = date_value.replace(tzinfo=UTC)

        local_time = date_value.astimezone(_LOCAL_TIMEZONE or None)
        return local_time.strftime(format_str)

    return str(date_value)


def nl2br(text: str) -> Markup:
    """Convert newlines to HTML <br> tags."""
    if not text:
        return Markup("")

    # Escape HTML to prevent XSS, then replace newlines with <br> tags
    escaped_text = escape(text)
    html = str(escaped_text).replace("\n", "<br>")
    return Markup(html)  # noqa: S704  # Text is escaped before markup conversion


def render_jinja(text: str) -> Markup:
    """Render a string as a Jinja template.

    This is useful for rendering template syntax stored in the database,
    such as wizard step titles that contain {{ _('...') }} translation calls.
    """
    if not text:
        return Markup("")

    from flask import render_template_string

    try:
        rendered = render_template_string(text)
        return Markup(rendered)  # noqa: S704  # render_template_string auto-escapes
    except Exception:
        # If rendering fails, return the original text escaped
        return Markup(escape(text))  # noqa: S704  # Text is explicitly escaped


def register_filters(app):
    """Register the custom Jinja filters on the given Flask *app*."""
    app.jinja_env.filters.setdefault("server_type_tag", server_type_tag)
    app.jinja_env.filters.setdefault("server_name_tag", server_name_tag)
    app.jinja_env.filters.setdefault("server_colour", _server_colour)
    app.jinja_env.filters.setdefault("human_date", human_date)
    app.jinja_env.filters.setdefault("local_date", local_date)
    app.jinja_env.filters.setdefault("nl2br", nl2br)
    app.jinja_env.filters.setdefault("render_jinja", render_jinja)

    # Add Python built-in functions to Jinja globals
    app.jinja_env.globals.setdefault("max", max)
    app.jinja_env.globals.setdefault("min", min)
