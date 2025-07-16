from markupsafe import Markup, escape

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
    return Markup(html)


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
    return Markup(html)


def register_filters(app):
    """Register the custom Jinja filters on the given Flask *app*."""
    app.jinja_env.filters.setdefault("server_type_tag", server_type_tag)
    app.jinja_env.filters.setdefault("server_name_tag", server_name_tag)
    app.jinja_env.filters.setdefault("server_colour", _server_colour)
